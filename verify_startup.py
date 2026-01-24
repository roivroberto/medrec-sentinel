import sys
import traceback


def verify_startup():
    print("Verifying Gradio App Startup...")
    try:
        from demo.gradio_app import build_demo
        build_demo()
        print("Build successful.")
    except Exception:
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify_startup()
