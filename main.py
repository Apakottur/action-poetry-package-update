#! /usr/bin/env python

def main():
    print("Success")
    with open("test.txt", "w") as f:
        f.write("blabla")


if __name__ == "__main__":
    main()
