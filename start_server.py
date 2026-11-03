import uvicorn
import os
import sys

if __name__ == "__main__":
    # Ensure current directory is on python path
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    if cur_dir not in sys.path:
        sys.path.insert(0, cur_dir)

    print("==================================================")
    print("🏥 Starting MediSync Hospital Dashboard System")
    print("🌐 Dashboard URL: http://127.0.0.1:8000")
    print("📖 API Documentation: http://127.0.0.1:8000/docs")
    print("==================================================")

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)

