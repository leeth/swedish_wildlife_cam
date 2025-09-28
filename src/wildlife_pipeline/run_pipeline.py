from __future__ import annotations
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from tqdm import tqdm
from PIL import Image

from .config import PipelineConfig
from .metadata import extract_exif, best_timestamp, infer_camera_id
from .ingest import iter_images
from .video_processor import VideoProcessor, iter_videos
from .detector import YOLODetector, BaseDetector, Detection
from .wildlife_detector import WildlifeDetector
from .megadetector import SwedishWildlifeDetector
from .utils import to_json
from .stages import filter_bboxes, crop_with_padding, is_doubtful
from .adapters.yolo_cls import YOLOClassifier

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
    # Stage-1 filtering & crops
    ap.add_argument("--stage1-conf", type=float, default=0.30)
    ap.add_argument("--min-rel-area", type=float, default=0.003)
    ap.add_argument("--max-rel-area", type=float, default=0.80)
    ap.add_argument("--min-aspect", type=float, default=0.2)
    ap.add_argument("--max-aspect", type=float, default=5.0)
    ap.add_argument("--edge-margin", type=int, default=12)
    ap.add_argument("--crop-padding", type=float, default=0.15)
    ap.add_argument("--save-crops", type=str, default=None, help="Directory to save crops; organize by <camera>/...")
    # Stage-2 classifier
    ap.add_argument("--stage2", type=str, default=None, help="Enable stage-2 classifier. Options: 'yolo_cls'")
    ap.add_argument("--stage2-weights", type=str, default=None, help="Weights for stage-2 classifier (e.g., yolov8n-cls.pt)")
    ap.add_argument("--stage2-conf", type=float, default=0.5, help="Confidence for stage-2 classifier")
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

    # Optional Stage-2 classifier initialization
    stage2_clf = None
    if args.stage2:
        if args.stage2.lower() == "yolo_cls":
            if not args.stage2_weights:
                raise SystemExit("--stage2-weights is required when --stage2 yolo_cls is set")
            stage2_clf = YOLOClassifier(args.stage2_weights, conf=args.stage2_conf)
        else:
            raise SystemExit(f"Unsupported --stage2 value: {args.stage2}")

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

            # Stage-1: filter detections and optionally write crops
            try:
                iw, ih = Image.open(img_path).size
            except Exception:
                iw, ih = (0, 0)

            filtered, dropped = filter_bboxes(
                detections,
                img_w=iw,
                img_h=ih,
                conf=args.stage1_conf,
                min_rel_area=args.min_rel_area,
                max_rel_area=args.max_rel_area,
                min_aspect=args.min_aspect,
                max_aspect=args.max_aspect,
                edge_margin_px=args.edge_margin,
            )

            # Save crops if requested
            if args.save_crops:
                out_root = Path(args.save_crops)
                out_dir = out_root / camera_id
                out_dir.mkdir(parents=True, exist_ok=True)
                for i, d in enumerate(filtered):
                    if d.bbox is None:
                        continue
                    crop_img, _box = crop_with_padding(img_path, d.bbox, pad_rel=args.crop_padding)
                    ts_safe = ts.strftime("%Y%m%dT%H%M%S") if hasattr(ts, "strftime") else str(ts)
                    fname = f"{ts_safe}_{i}_{d.label}_{d.confidence:.2f}.jpg"
                    out_path = out_dir / fname
                    try:
                        crop_img.save(out_path, format="JPEG", quality=90)
                    except Exception:
                        pass

            # Stage-1 decision split: confident -> candidate_for_stage2; doubtful -> manual
            manual_review = []
            candidate_for_stage2 = []
            try:
                iw, ih = Image.open(img_path).size
            except Exception:
                iw, ih = (0, 0)
            for d in filtered:
                if is_doubtful(d, iw, ih, conf_threshold=args.stage1_conf, edge_margin_px=args.edge_margin,
                               tiny_rel=0.01, min_rel_area=args.min_rel_area):
                    manual_review.append(d)
                else:
                    candidate_for_stage2.append(d)

            # Stage-2 (optional) runs only on confident candidates
            observations_stage2 = None
            if stage2_clf and candidate_for_stage2:
                obs2 = []
                for d in candidate_for_stage2:
                    if d.bbox is None:
                        continue
                    crop_img, _box = crop_with_padding(img_path, d.bbox, pad_rel=args.crop_padding)
                    try:
                        cls_res = stage2_clf.predict_image(crop_img)
                        obs2.append({
                            "label": cls_res.label,
                            "confidence": cls_res.confidence,
                            "bbox": d.bbox,
                        })
                    except Exception:
                        continue
                observations_stage2 = to_json(obs2)

            row = row_from_detections(img_path, camera_id, ts, filtered)
            row["stage1_dropped"] = dropped
            if manual_review:
                row["manual_review_count"] = len(manual_review)
            if observations_stage2 is not None:
                row["observations_stage2"] = observations_stage2
            rows.append(row)
    
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
                    
                    # Also add individual frame results with Stage-1/2 processing
                    for frame in video_frames:
                        if not frame.detections:
                            continue

                        # Stage-1 filtering on frame detections
                        try:
                            if frame.image_path is not None:
                                iw, ih = Image.open(frame.image_path).size
                            else:
                                iw, ih = (0, 0)
                        except Exception:
                            iw, ih = (0, 0)

                        filtered_f, dropped_f = filter_bboxes(
                            frame.detections,
                            img_w=iw,
                            img_h=ih,
                            conf=args.stage1_conf,
                            min_rel_area=args.min_rel_area,
                            max_rel_area=args.max_rel_area,
                            min_aspect=args.min_aspect,
                            max_aspect=args.max_aspect,
                            edge_margin_px=args.edge_margin,
                        )

                        # Stage-1 decision split for frame
                        manual_review_f = []
                        candidate_for_stage2_f = []
                        for d in filtered_f:
                            if is_doubtful(d, iw, ih, conf_threshold=args.stage1_conf, edge_margin_px=args.edge_margin,
                                           tiny_rel=0.01, min_rel_area=args.min_rel_area):
                                manual_review_f.append(d)
                            else:
                                candidate_for_stage2_f.append(d)

                        # Stage-2 classification per confident bbox (optional)
                        observations_stage2_f = None
                        if stage2_clf and candidate_for_stage2_f:
                            obs2f = []
                            for d in candidate_for_stage2_f:
                                if d.bbox is None:
                                    continue
                                crop_img, _box = crop_with_padding(frame.image_path or video_path, d.bbox, pad_rel=args.crop_padding)
                                try:
                                    cls_res = stage2_clf.predict_image(crop_img)
                                    obs2f.append({
                                        "label": cls_res.label,
                                        "confidence": cls_res.confidence,
                                        "bbox": d.bbox,
                                    })
                                except Exception:
                                    continue
                            observations_stage2_f = to_json(obs2f)

                        # Save crops for frame if requested
                        if args.save_crops and filtered_f:
                            cam_id = infer_camera_id(video_path, cfg.input_root)
                            out_root = Path(args.save_crops)
                            out_dir = out_root / cam_id
                            out_dir.mkdir(parents=True, exist_ok=True)
                            ts_video = best_timestamp(video_path, None)
                            ts_safe = ts_video.strftime("%Y%m%dT%H%M%S") if hasattr(ts_video, "strftime") else str(ts_video)
                            for i, d in enumerate(filtered_f):
                                if d.bbox is None:
                                    continue
                                crop_img, _box = crop_with_padding(frame.image_path or video_path, d.bbox, pad_rel=args.crop_padding)
                                fname = f"{ts_safe}_f{frame.frame_number}_{i}_{d.label}_{d.confidence:.2f}.jpg"
                                out_path = out_dir / fname
                                try:
                                    crop_img.save(out_path, format="JPEG", quality=90)
                                except Exception:
                                    pass

                        frame_row = row_from_detections(
                            frame.image_path or video_path,
                            infer_camera_id(video_path, cfg.input_root),
                            best_timestamp(video_path, None),
                            filtered_f,
                        )
                        frame_row["file_type"] = "video_frame"
                        frame_row["video_source"] = str(video_path)
                        frame_row["frame_number"] = frame.frame_number
                        frame_row["frame_timestamp"] = frame.timestamp
                        frame_row["stage1_dropped"] = dropped_f
                        if manual_review_f:
                            frame_row["manual_review_count"] = len(manual_review_f)
                        if observations_stage2_f is not None:
                            frame_row["observations_stage2"] = observations_stage2_f
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
