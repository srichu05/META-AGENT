# test_torch.py
import sys

print("\n🧪 Testing PyTorch Installation\n")

try:
    import torch
    print(f"✅ torch imported: version {torch.__version__}")
    
    x = torch.randn(3, 4)
    print(f"✅ Created tensor: shape {x.shape}")
    
    print("\n✅ PYTORCH WORKING!\n")
except Exception as e:
    print(f"❌ PYTORCH FAILED: {str(e)}\n")
    sys.exit(1)
