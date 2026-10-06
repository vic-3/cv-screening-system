from document_reader import read_document, clean_text


def main():
    file_path = input("Enter the CV file path: ")

    try:
        cv_text = read_document(file_path)
        cv_text = clean_text(cv_text)
    

        print("\n" + "=" * 60)
        print("EXTRACTED CV TEXT")
        print("=" * 60)

        print(cv_text)

        print("\n" + "=" * 60)
        print("DOCUMENT INFORMATION")
        print("=" * 60)

        print(f"Characters: {len(cv_text)}")
        print(f"Words: {len(cv_text.split())}")

    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()