import merge_all
import sys

def main():
    university = "Saint Louis University"
    print(f"Running merge for {university}")
    for status in merge_all.run(university):
        print(status)
        sys.stdout.flush()

if __name__ == "__main__":
    main()
