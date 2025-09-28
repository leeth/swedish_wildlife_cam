from __future__ import annotations
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from tqdm import tqdm

from .config import PipelineConfig
from .metadata import extract_exif, best_timestamp, infer_camera_id
from .ingest import iter_images
from .video_processor import VideoProcessor, iter_videos
from .detector import YOLODetector, BaseDetector, Detection
from .wildlife_detector import WildlifeDetector
from .megadetector import SwedishWildlifeDetector
from .utils import to_json

def build_detector(cfg: PipelineConfig) -> BaseDetector:
    if not cfg.model_path:
        raise SystemExit("No model path provided. Use --model <path/to/model.pt>")
    
    # Check if using Swedish Wildlife Detector
    if cfg.model_path.lower() in ['megadetector', 'md', 'mega', 'swedish']:
        print("Using Swedish Wildlife Detector for Swedish wildlife detection...")
        return SwedishWildlifeDetector(conf=cfg.conf_thres)
    
    # Use WildlifeDetector for better wildlife classification with YOLO models
    return WildlifeDetector(cfg.model_path, conf=cfg.conf_thres, iou=cfg.iou_thres)

def row_from_detections(
    image_path: Path,
    camera_id: str,
    ts,
    detections: List[Detection],
) -> Dict[str, Any]:
    observation_any = len(detections) > 0
    top_label: Optional[str] = None
    top_conf: Optional[float] = None
    if observation_any:
        top = max(detections, key=lambda d: d.confidence)
        top_label, top_conf = top.label, top.confidence

    obs_payload = [
        {"label": d.label, "confidence": d.confidence, "bbox": d.bbox}
        for d in detections
    ]

    return {
        "image_path": str(image_path),
        "camera_id": camera_id,
        "timestamp": ts.isoformat(),
        "observation_any": observation_any,
        "observations": to_json(obs_payload),
        "top_label": top_label,
        "top_confidence": top_conf,
    }

def main():
    ap = argparse.ArgumentParser(description="Wildlife image pipeline")
    ap.add_argument("--input", required=True, help="Root folder of camera images")
    ap.add_argument("--output", required=True, help="Output file (.csv or .parquet)")
    ap.add_argument("--model", required=True, help="Path to YOLO model .pt or 'megadetector' for Swedish Wildlife Detector")
    ap.add_argument("--conf-thres", type=float, default=0.35)
    ap.add_argument("--iou-thres", type=float, default=0.5)
    ap.add_argument("--write", choices=["csv", "parquet"], default="csv")
    ap.add_argument("--preview", type=int, default=0, help="Preview N images then exit")
    ap.add_argument("--frame-interval", type=int, default=30, help="Extract every Nth frame from videos (default: 30)")
    ap.add_argument("--max-frames", type=int, default=100, help="Maximum frames to extract per video (default: 100)")
    ap.add_argument("--process-videos", action="store_true", help="Process video files in addition to images")
    args = ap.parse_args()

    cfg = PipelineConfig(
        input_root=Path(args.input),
        output_path=Path(args.output),
        model_path=args.model,
        conf_thres=args.conf_thres,
        iou_thres=args.iou_thres,
        write_format=args.write,
    )

    det = build_detector(cfg)

    rows: List[Dict[str, Any]] = []
    
    # Process images
    image_exts = [".jpg", ".jpeg", ".png", ".bmp"]
    video_exts = [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"]
    
    # Process images
    image_files = list(iter_images(cfg.input_root, image_exts))
    if image_files:
        print(f"Found {len(image_files)} image files")
        
        if args.preview > 0:
            from itertools import islice
            image_files = list(islice(image_files, args.preview))

        for img_path in tqdm(image_files, desc="Processing images"):
            exif = extract_exif(img_path)
            ts = best_timestamp(img_path, exif)
            camera_id = infer_camera_id(img_path, cfg.input_root)
            detections = det.predict(img_path)
            rows.append(row_from_detections(img_path, camera_id, ts, detections))
    
    # Process videos if requested
    if args.process_videos:
        video_files = list(iter_videos(cfg.input_root, video_exts))
        if video_files:
            print(f"Found {len(video_files)} video files")
            
            # Initialize video processor
            video_processor = VideoProcessor(
                detector=det,
                frame_interval=args.frame_interval,
                max_frames=args.max_frames
            )
            
            try:
                for video_path in tqdm(video_files, desc="Processing videos"):
                    # Process video and extract frames
                    video_frames = video_processor.process_video(video_path)
                    
                    # Create summary for video
                    summary = video_processor.summarize_video_detections(video_frames)
                    
                    # Add video summary to results
                    video_row = {
                        "file_path": str(video_path),
                        "file_type": "video",
                        "camera_id": infer_camera_id(video_path, cfg.input_root),
                        "timestamp": best_timestamp(video_path, None),
                        "total_frames": summary["total_frames"],
                        "frames_with_detections": summary["frames_with_detections"],
                        "total_detections": summary["total_detections"],
                        "detection_rate": summary["detection_rate"],
                        "species_detected": to_json(summary["species_detected"]),
                        "detection_timeline": to_json(summary["detection_timeline"]),
                        "observation_any": summary["total_detections"] > 0
                    }
                    
                    rows.append(video_row)
                    
                    # Also add individual frame results if requested
                    for frame in video_frames:
                        if frame.detections:  # Only add frames with detections
                            frame_row = row_from_detections(
                                frame.image_path or video_path,
                                infer_camera_id(video_path, cfg.input_root),
                                best_timestamp(video_path, None),
                                frame.detections
                            )
                            frame_row["file_type"] = "video_frame"
                            frame_row["video_source"] = str(video_path)
                            frame_row["frame_number"] = frame.frame_number
                            frame_row["frame_timestamp"] = frame.timestamp
                            rows.append(frame_row)
            
            finally:
                # Clean up temporary files
                video_processor.cleanup_temp_files()
    
    if not rows:
        print("No files found. Check --input or file extensions.")
        return

    df = pd.DataFrame(rows)
    out = cfg.output_path
    out.parent.mkdir(parents=True, exist_ok=True)

    if cfg.write_format == "parquet" or out.suffix.lower() == ".parquet":
        df.to_parquet(out, index=False)
    else:
        df.to_csv(out, index=False)

    print(f"Wrote {len(df)} rows to {out}")

if __name__ == "__main__":
    main()
