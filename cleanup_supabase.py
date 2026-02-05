from supabase import create_client

SUPABASE_URL = "https://rjfjtthpqeozbxsqnqpv.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZmp0dGhwcWVvemJ4c3FucXB2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzc0MTE5OCwiZXhwIjoyMDY5MzE3MTk4fQ.qf8YZQZ1h6PGzxtohGcwVxnv5AH9WAzz8DbVcv6Ddno"
BUCKET_NAME = "audio-recordings"  # change if needed

supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)


def list_folder(path=""):
    return supabase.storage.from_(BUCKET_NAME).list(path, {"limit": 1000})


def get_all_files(folder=""):
    total_size = 0
    items = list_folder(folder)

    for item in items:
        name = item["name"]
        full_path = f"{folder}/{name}" if folder else name

        # Files have metadata, folders don't
        if item.get("metadata"):
            total_size += item["metadata"]["size"]
        else:
            total_size += get_all_files(full_path)

    return total_size


def main():
    print("Scanning bucket... please wait.")
    total_bytes = get_all_files()
    total_gb = total_bytes / (1024 ** 3)

    print(f"\nActual storage used in bucket '{BUCKET_NAME}':")
    print(f"{total_bytes:,} bytes")
    print(f"{total_gb:.2f} GB")


if __name__ == "__main__":
    main()
