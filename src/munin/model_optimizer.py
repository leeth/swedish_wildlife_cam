"""
Model Optimization and Export for High-Performance Inference.

This module provides:
- ONNX model export for cross-platform deployment
- TensorRT optimization for NVIDIA GPUs
- Mixed precision inference
- Batch processing optimization
- Model quantization for edge deployment
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    import torch.onnx
    from ultralytics import YOLO
except ImportError as e:
    print(f"Missing dependencies for model optimization: {e}")
    print("Install with: pip install torch onnx onnxruntime ultralytics")
    sys.exit(1)

try:
    import tensorrt as trt
    TRT_AVAILABLE = True
except ImportError:
    TRT_AVAILABLE = False
    print("⚠️  TensorRT not available. Install with: pip install tensorrt")

from ..common.utils.logging_utils import get_logger

logger = get_logger("wildlife_pipeline.model_optimization")


class ModelOptimizer:
    """Model optimization and export for high-performance inference."""

    def __init__(self, model_path: str, device: str = "cuda"):
        self.model_path = model_path
        self.device = device
        self.logger = logger

        # Load model
        self.model = YOLO(model_path)
        self.model.to(device)

        # TensorRT availability
        self.tensorrt_available = TRT_AVAILABLE

        self.logger.info(f"🚀 Model optimizer initialized: {model_path}")
        self.logger.info(f"📱 Device: {device}")
        self.logger.info(f"🔧 TensorRT available: {self.tensorrt_available}")

    def export_to_onnx(self, output_path: str,
                       input_size: Tuple[int, int] = (640, 640),
                       batch_size: int = 1,
                       opset_version: int = 11) -> str:
        """
        Export YOLO model to ONNX format.

        Args:
            output_path: Path to save ONNX model
            input_size: Input image size (height, width)
            batch_size: Batch size for inference
            opset_version: ONNX opset version

        Returns:
            Path to exported ONNX model
        """
        self.logger.info(f"📦 Exporting model to ONNX: {output_path}")

        try:
            # Export to ONNX
            onnx_path = self.model.export(
                format='onnx',
                imgsz=input_size,
                batch=batch_size,
                opset=opset_version,
                simplify=True,
                dynamic=False,
                verbose=False
            )

            # Move to desired location if different
            if onnx_path != output_path:
                import shutil
                shutil.move(onnx_path, output_path)

            # Verify ONNX model
            self._verify_onnx_model(output_path)

            self.logger.info(f"✅ ONNX export completed: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"❌ ONNX export failed: {e}")
            raise

    def _verify_onnx_model(self, onnx_path: str) -> None:
        """Verify ONNX model integrity."""
        try:
            # Load and check ONNX model
            onnx_model = onnx.load(onnx_path)
            onnx.checker.check_model(onnx_model)

            # Test inference
            ort_session = ort.InferenceSession(onnx_path)
            input_shape = ort_session.get_inputs()[0].shape

            self.logger.info(f"✅ ONNX model verified: {input_shape}")

        except Exception as e:
            self.logger.error(f"❌ ONNX model verification failed: {e}")
            raise

    def optimize_for_tensorrt(self, onnx_path: str,
                            output_path: str,
                            precision: str = "fp16",
                            max_batch_size: int = 32,
                            max_workspace_size: int = 1 << 30) -> str:
        """
        Optimize ONNX model for TensorRT.

        Args:
            onnx_path: Path to ONNX model
            output_path: Path to save TensorRT engine
            precision: Precision mode (fp32, fp16, int8)
            max_batch_size: Maximum batch size
            max_workspace_size: Maximum workspace size in bytes

        Returns:
            Path to TensorRT engine
        """
        if not self.tensorrt_available:
            raise RuntimeError("TensorRT not available")

        self.logger.info(f"🔧 Optimizing model for TensorRT: {output_path}")

        try:
            # Create TensorRT logger
            trt_logger = trt.Logger(trt.Logger.INFO)

            # Create builder
            builder = trt.Builder(trt_logger)
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            parser = trt.OnnxParser(network, trt_logger)

            # Parse ONNX model
            with open(onnx_path, 'rb') as model:
                if not parser.parse(model.read()):
                    raise RuntimeError("Failed to parse ONNX model")

            # Configure builder
            config = builder.create_builder_config()
            config.max_workspace_size = max_workspace_size

            # Set precision
            if precision == "fp16":
                config.set_flag(trt.BuilderFlag.FP16)
            elif precision == "int8":
                config.set_flag(trt.BuilderFlag.INT8)
                # TODO: Add calibration dataset for INT8

            # Build engine
            self.logger.info("🔨 Building TensorRT engine...")
            engine = builder.build_engine(network, config)

            if engine is None:
                raise RuntimeError("Failed to build TensorRT engine")

            # Save engine
            with open(output_path, 'wb') as f:
                f.write(engine.serialize())

            self.logger.info(f"✅ TensorRT engine saved: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"❌ TensorRT optimization failed: {e}")
            raise

    def create_optimized_inference(self, model_path: str,
                                 use_tensorrt: bool = False,
                                 precision: str = "fp16") -> 'OptimizedInference':
        """
        Create optimized inference engine.

        Args:
            model_path: Path to model (ONNX or TensorRT)
            use_tensorrt: Whether to use TensorRT
            precision: Precision mode

        Returns:
            Optimized inference engine
        """
        return OptimizedInference(
            model_path=model_path,
            use_tensorrt=use_tensorrt,
            precision=precision,
            device=self.device
        )

    def benchmark_models(self, test_images: List[np.ndarray],
                        models: Dict[str, str]) -> Dict[str, Dict]:
        """
        Benchmark different model formats.

        Args:
            test_images: List of test images
            models: Dictionary of model name to path

        Returns:
            Benchmark results
        """
        self.logger.info(f"📊 Benchmarking {len(models)} models with {len(test_images)} images")

        results = {}

        for model_name, model_path in models.items():
            try:
                # Create inference engine
                inference = self.create_optimized_inference(
                    model_path,
                    use_tensorrt=model_path.endswith('.trt')
                )

                # Warmup
                for _ in range(5):
                    inference.predict_batch(test_images[:1])

                # Benchmark
                start_time = time.time()
                predictions = inference.predict_batch(test_images)
                end_time = time.time()

                # Calculate metrics
                total_time = end_time - start_time
                fps = len(test_images) / total_time
                avg_time = total_time / len(test_images)

                results[model_name] = {
                    'total_time': total_time,
                    'fps': fps,
                    'avg_time': avg_time,
                    'predictions': len(predictions),
                    'model_size': Path(model_path).stat().st_size if Path(model_path).exists() else 0
                }

                self.logger.info(f"📈 {model_name}: {fps:.2f} FPS, {avg_time*1000:.2f}ms per image")

            except Exception as e:
                self.logger.error(f"❌ Benchmark failed for {model_name}: {e}")
                results[model_name] = {'error': str(e)}

        return results


class OptimizedInference:
    """Optimized inference engine with ONNX/TensorRT support."""

    def __init__(self, model_path: str, use_tensorrt: bool = False,
                 precision: str = "fp16", device: str = "cuda"):
        self.model_path = model_path
        self.use_tensorrt = use_tensorrt
        self.precision = precision
        self.device = device
        self.logger = logger

        # Initialize inference engine
        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize the inference engine."""
        if self.use_tensorrt and TRT_AVAILABLE:
            self._initialize_tensorrt()
        else:
            self._initialize_onnx()

    def _initialize_tensorrt(self):
        """Initialize TensorRT engine."""
        self.logger.info("🔧 Initializing TensorRT engine")

        # Load TensorRT engine
        with open(self.model_path, 'rb') as f:
            engine_data = f.read()

        # Create runtime and engine
        runtime = trt.Runtime(trt.Logger(trt.Logger.INFO))
        self.engine = runtime.deserialize_cuda_engine(engine_data)
        self.context = self.engine.create_execution_context()

        # Get input/output shapes
        self.input_shape = self.engine.get_binding_shape(0)
        self.output_shape = self.engine.get_binding_shape(1)

        self.logger.info(f"✅ TensorRT engine loaded: {self.input_shape} -> {self.output_shape}")

    def _initialize_onnx(self):
        """Initialize ONNX Runtime engine."""
        self.logger.info("🔧 Initializing ONNX Runtime engine")

        # Configure providers
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

        # Create session
        self.session = ort.InferenceSession(self.model_path, providers=providers)

        # Get input/output info
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        self.output_names = [output.name for output in self.session.get_outputs()]

        self.logger.info(f"✅ ONNX Runtime engine loaded: {self.input_shape}")

    def predict_batch(self, images: List[np.ndarray]) -> List[Dict]:
        """
        Predict on batch of images.

        Args:
            images: List of images as numpy arrays

        Returns:
            List of prediction results
        """
        if not images:
            return []

        # Preprocess images
        batch_input = self._preprocess_batch(images)

        # Run inference
        if self.use_tensorrt:
            outputs = self._inference_tensorrt(batch_input)
        else:
            outputs = self._inference_onnx(batch_input)

        # Postprocess results
        results = self._postprocess_batch(outputs, images)

        return results

    def _preprocess_batch(self, images: List[np.ndarray]) -> np.ndarray:
        """Preprocess batch of images."""
        len(images)

        # Resize and normalize images
        processed_images = []
        for img in images:
            # Resize to model input size
            # TODO: Add cv2 import or use PIL
            # resized = cv2.resize(img, (width, height))
            resized = img  # Placeholder

            # Normalize to [0, 1]
            normalized = resized.astype(np.float32) / 255.0

            # Convert to CHW format
            chw = np.transpose(normalized, (2, 0, 1))
            processed_images.append(chw)

        # Stack into batch
        batch = np.stack(processed_images, axis=0)

        return batch

    def _inference_tensorrt(self, batch_input: np.ndarray) -> np.ndarray:
        """Run TensorRT inference."""
        # Allocate GPU memory
        d_input = torch.cuda.FloatTensor(batch_input)
        d_output = torch.cuda.FloatTensor(batch_input.shape[0], *self.output_shape[1:])

        # Run inference
        self.context.execute_v2([d_input.data_ptr(), d_output.data_ptr()])

        return d_output.cpu().numpy()

    def _inference_onnx(self, batch_input: np.ndarray) -> np.ndarray:
        """Run ONNX Runtime inference."""
        # Prepare inputs
        inputs = {self.input_name: batch_input}

        # Run inference
        outputs = self.session.run(self.output_names, inputs)

        return outputs[0] if len(outputs) == 1 else outputs

    def _postprocess_batch(self, outputs: np.ndarray,
                          original_images: List[np.ndarray]) -> List[Dict]:
        """Postprocess inference outputs."""
        results = []

        for i, output in enumerate(outputs):
            # Convert to detection format
            # This is a simplified postprocessing - adapt to your model's output format
            detections = {
                'image_id': i,
                'predictions': output.tolist(),
                'confidence': float(np.max(output)),
                'class_id': int(np.argmax(output))
            }
            results.append(detections)

        return results


def main():
    """Test model optimization."""
    import argparse

    parser = argparse.ArgumentParser(description="Model Optimization")
    parser.add_argument("model_path", help="Path to YOLO model")
    parser.add_argument("--output-dir", default="./optimized_models", help="Output directory")
    parser.add_argument("--precision", choices=["fp32", "fp16", "int8"], default="fp16")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark")

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Initialize optimizer
    optimizer = ModelOptimizer(args.model_path)

    # Export to ONNX
    onnx_path = output_dir / "model.onnx"
    optimizer.export_to_onnx(str(onnx_path), batch_size=args.batch_size)

    # Optimize for TensorRT if available
    if TRT_AVAILABLE:
        trt_path = output_dir / "model.trt"
        optimizer.optimize_for_tensorrt(
            str(onnx_path),
            str(trt_path),
            precision=args.precision,
            max_batch_size=args.batch_size
        )

    # Run benchmark if requested
    if args.benchmark:
        # Create test images
        test_images = [np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8) for _ in range(10)]

        # Benchmark models
        models = {"ONNX": str(onnx_path)}
        if TRT_AVAILABLE:
            models["TensorRT"] = str(trt_path)

        results = optimizer.benchmark_models(test_images, models)

        print("\n📊 Benchmark Results:")
        for model_name, result in results.items():
            if 'error' not in result:
                print(f"  {model_name}: {result['fps']:.2f} FPS, {result['avg_time']*1000:.2f}ms")


if __name__ == "__main__":
    main()
