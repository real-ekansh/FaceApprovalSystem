import os
import sys

PLATFORMS = {
    "render": [
        "app.py",
        "requirements.txt",
        "Procfile",
        "static/",
        "templates/",
    ],
    "heroku": [
        "app.py",
        "requirements.txt",
        "Procfile",
        "static/",
        "templates/",
        # "runtime.txt" # optional
    ],
    "docker": [
        "app.py",
        "requirements.txt",
        "Dockerfile",
        "static/",
        "templates/",
    ],
    "vercel": [
        "api/faceapproval.py",
        "requirements.txt",
        "public/",   # static assets here on Vercel
        # "vercel.json", # optional (advanced routing)
    ],
    "local": [
        "app.py",
        "requirements.txt",
        "static/",
        "templates/",
        "run.py",
    ],
}

def check_presence(path, is_folder=None):
    if is_folder or (is_folder is None and path.endswith('/')):
        exists = os.path.isdir(path.rstrip('/'))
    else:
        exists = os.path.isfile(path)
    return exists

def run_platform_check(platform):
    print(f"\nChecking files for platform: {platform.upper()}")
    checklist = PLATFORMS.get(platform)
    if not checklist:
        print(f"Unknown platform: {platform}")
        sys.exit(1)

    all_good = True
    for item in checklist:
        is_folder = item.endswith("/")
        present = check_presence(item, is_folder)
        status = "✅" if present else "❌"
        print(f"{status} {item}")
        if not present:
            all_good = False
    if all_good:
        print("\n🎉 All required files are present for", platform.capitalize())
    else:
        print("\n⚠️  Please add the missing files/folders for", platform.capitalize())

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Health check for deployment files")
    parser.add_argument("--platform", type=str, choices=PLATFORMS.keys(), default="local",
                        help="Deployment platform to check (default: local)")
    args = parser.parse_args()
    run_platform_check(args.platform)
