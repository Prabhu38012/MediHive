import os
import sys
import importlib.util

# Hugging Face ZeroGPU compatibility
try:
    import spaces
    @spaces.GPU(duration=15)
    def _hf_zerogpu_ready():
        return True
except ImportError:
    pass

# Ensure MediHive is on the path and is the working directory
root_dir = os.path.dirname(os.path.abspath(__file__))
medihive_dir = os.path.join(root_dir, "MediHive")

if medihive_dir not in sys.path:
    sys.path.insert(0, medihive_dir)

os.chdir(medihive_dir)

# Dynamically load the core FastAPI app from MediHive/app.py without name collision
spec = importlib.util.spec_from_file_location("medihive_backend", os.path.join(medihive_dir, "app.py"))
medihive_backend = importlib.util.module_from_spec(spec)
sys.modules["medihive_backend"] = medihive_backend
spec.loader.exec_module(medihive_backend)

app = medihive_backend.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting MedTrustAI on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
