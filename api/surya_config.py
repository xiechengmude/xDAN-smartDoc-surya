#!/usr/bin/env python3
"""
Surya OCR 性能优化配置
根据硬件环境自动调整批处理大小和其他性能参数
"""

import os
import torch
from surya.settings import settings


class SuryaOptimizer:
    """Surya性能优化器"""
    
    def __init__(self):
        self.device = settings.TORCH_DEVICE_MODEL
        self.available_memory = self._get_available_memory()
        
    def _get_available_memory(self) -> int:
        """获取可用显存或内存（MB）"""
        if self.device == "cuda":
            if torch.cuda.is_available():
                return torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
        elif self.device == "mps":
            # MPS设备的内存检测比较复杂，使用保守估计
            return 8192  # 8GB
        else:
            # CPU模式，使用系统内存
            import psutil
            return psutil.virtual_memory().total // (1024 * 1024)
        return 4096  # 默认4GB
    
    def get_optimal_batch_sizes(self) -> dict:
        """根据硬件配置获取最优批处理大小"""
        memory_gb = self.available_memory / 1024
        
        if self.device == "cuda":
            # GPU优化配置
            if memory_gb >= 24:  # 24GB+ GPU (A100, RTX 4090等)
                return {
                    "DETECTOR_BATCH_SIZE": 64,
                    "RECOGNITION_BATCH_SIZE": 512,
                    "LAYOUT_BATCH_SIZE": 64,
                    "TABLE_REC_BATCH_SIZE": 128
                }
            elif memory_gb >= 16:  # 16GB GPU (RTX 4080, A4000等)
                return {
                    "DETECTOR_BATCH_SIZE": 48,
                    "RECOGNITION_BATCH_SIZE": 384,
                    "LAYOUT_BATCH_SIZE": 48,
                    "TABLE_REC_BATCH_SIZE": 96
                }
            elif memory_gb >= 12:  # 12GB GPU (RTX 4070 Ti, RTX 3080等)
                return {
                    "DETECTOR_BATCH_SIZE": 36,
                    "RECOGNITION_BATCH_SIZE": 256,
                    "LAYOUT_BATCH_SIZE": 32,
                    "TABLE_REC_BATCH_SIZE": 64
                }
            elif memory_gb >= 8:   # 8GB GPU (RTX 4060 Ti, RTX 3070等)
                return {
                    "DETECTOR_BATCH_SIZE": 24,
                    "RECOGNITION_BATCH_SIZE": 128,
                    "LAYOUT_BATCH_SIZE": 24,
                    "TABLE_REC_BATCH_SIZE": 48
                }
            else:  # 6GB及以下GPU
                return {
                    "DETECTOR_BATCH_SIZE": 12,
                    "RECOGNITION_BATCH_SIZE": 64,
                    "LAYOUT_BATCH_SIZE": 16,
                    "TABLE_REC_BATCH_SIZE": 32
                }
        
        elif self.device == "mps":
            # Apple Silicon优化配置
            return {
                "DETECTOR_BATCH_SIZE": 8,
                "RECOGNITION_BATCH_SIZE": 32,
                "LAYOUT_BATCH_SIZE": 8,
                "TABLE_REC_BATCH_SIZE": 16
            }
        
        else:
            # CPU优化配置
            cpu_count = os.cpu_count() or 4
            if cpu_count >= 16:
                return {
                    "DETECTOR_BATCH_SIZE": 8,
                    "RECOGNITION_BATCH_SIZE": 16,
                    "LAYOUT_BATCH_SIZE": 6,
                    "TABLE_REC_BATCH_SIZE": 12
                }
            elif cpu_count >= 8:
                return {
                    "DETECTOR_BATCH_SIZE": 6,
                    "RECOGNITION_BATCH_SIZE": 12,
                    "LAYOUT_BATCH_SIZE": 4,
                    "TABLE_REC_BATCH_SIZE": 8
                }
            else:
                return {
                    "DETECTOR_BATCH_SIZE": 2,
                    "RECOGNITION_BATCH_SIZE": 4,
                    "LAYOUT_BATCH_SIZE": 2,
                    "TABLE_REC_BATCH_SIZE": 4
                }
    
    def get_optimal_worker_counts(self) -> dict:
        """获取最优工作线程数"""
        cpu_count = os.cpu_count() or 4
        
        return {
            "DETECTOR_POSTPROCESSING_CPU_WORKERS": min(8, cpu_count),
            "PARALLEL_DOWNLOAD_WORKERS": min(10, cpu_count),
            "IMAGE_PROCESSING_WORKERS": min(4, cpu_count // 2)
        }
    
    def get_compilation_settings(self) -> dict:
        """获取编译优化设置"""
        # 只在支持的设备上启用编译
        if self.device == "cuda" and self.available_memory > 8192:
            return {
                "COMPILE_DETECTOR": True,
                "COMPILE_LAYOUT": True,
                "COMPILE_TABLE_REC": True,
                "COMPILE_ALL": False  # 避免过度编译
            }
        else:
            return {
                "COMPILE_DETECTOR": False,
                "COMPILE_LAYOUT": False,
                "COMPILE_TABLE_REC": False,
                "COMPILE_ALL": False
            }
    
    def apply_optimizations(self):
        """应用所有优化设置"""
        print(f"🔧 正在优化Surya配置...")
        print(f"   设备: {self.device}")
        print(f"   可用内存: {self.available_memory} MB")
        
        # 应用批处理大小优化
        batch_sizes = self.get_optimal_batch_sizes()
        for key, value in batch_sizes.items():
            os.environ[key] = str(value)
            print(f"   {key}: {value}")
        
        # 应用工作线程数优化
        worker_counts = self.get_optimal_worker_counts()
        for key, value in worker_counts.items():
            os.environ[key] = str(value)
            print(f"   {key}: {value}")
        
        # 应用编译设置
        compilation_settings = self.get_compilation_settings()
        for key, value in compilation_settings.items():
            os.environ[key] = str(value).lower()
            if value:
                print(f"   {key}: {value}")
        
        # 其他性能优化设置
        performance_settings = {
            "PYTORCH_ENABLE_MPS_FALLBACK": "1",  # MPS回退支持
            "OMP_NUM_THREADS": str(min(8, os.cpu_count() or 4)),  # OpenMP线程数
            "TOKENIZERS_PARALLELISM": "false",  # 避免tokenizer警告
        }
        
        for key, value in performance_settings.items():
            os.environ[key] = value
        
        print("✅ Surya配置优化完成")
    
    def get_recommended_api_settings(self) -> dict:
        """获取推荐的API服务设置"""
        memory_gb = self.available_memory / 1024
        cpu_count = os.cpu_count() or 4
        
        if self.device == "cuda" and memory_gb >= 16:
            max_concurrent = min(8, cpu_count // 2)
        elif self.device == "cuda" and memory_gb >= 8:
            max_concurrent = min(5, cpu_count // 2)
        elif self.device == "mps":
            max_concurrent = min(3, cpu_count // 4)
        else:
            max_concurrent = min(2, cpu_count // 4)
        
        batch_sizes = self.get_optimal_batch_sizes()
        return {
            "max_concurrent_tasks": max_concurrent,
            "default_batch_size": batch_sizes.get("RECOGNITION_BATCH_SIZE", 32) // 4,
            "thread_pool_workers": min(32, cpu_count + 4)
        }


def setup_environment_variables():
    """设置环境变量以优化性能"""
    optimizer = SuryaOptimizer()
    optimizer.apply_optimizations()
    return optimizer.get_recommended_api_settings()


if __name__ == "__main__":
    # 直接运行此脚本来查看推荐配置
    optimizer = SuryaOptimizer()
    
    print("🔍 Surya性能分析报告")
    print("=" * 50)
    print(f"设备类型: {optimizer.device}")
    print(f"可用内存: {optimizer.available_memory} MB ({optimizer.available_memory/1024:.1f} GB)")
    print(f"CPU核心数: {os.cpu_count()}")
    print()
    
    print("📊 推荐批处理大小:")
    batch_sizes = optimizer.get_optimal_batch_sizes()
    for key, value in batch_sizes.items():
        print(f"  {key}: {value}")
    print()
    
    print("⚙️ 推荐工作线程数:")
    worker_counts = optimizer.get_optimal_worker_counts()
    for key, value in worker_counts.items():
        print(f"  {key}: {value}")
    print()
    
    print("🚀 推荐编译设置:")
    compilation_settings = optimizer.get_compilation_settings()
    for key, value in compilation_settings.items():
        if value:
            print(f"  {key}: {value}")
    print()
    
    print("🌐 推荐API服务设置:")
    api_settings = optimizer.get_recommended_api_settings()
    for key, value in api_settings.items():
        print(f"  {key}: {value}")
    print()
    
    print("💡 使用建议:")
    if optimizer.device == "cuda":
        print("  - GPU加速已启用，建议使用较大的批处理大小")
        print("  - 考虑启用模型编译以获得更好性能")
    elif optimizer.device == "mps":
        print("  - Apple Silicon加速已启用")
        print("  - 使用适中的批处理大小以避免内存问题")
    else:
        print("  - 使用CPU模式，建议使用较小的批处理大小")
        print("  - 考虑增加CPU工作线程数")
    
    print("  - 根据实际使用情况调整max_concurrent_tasks参数")
    print("  - 监控内存使用情况，必要时减少批处理大小") 