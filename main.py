#! /usr/bin/env python
import os

import shpyx


def main():
    print(os.listdir())
    with open("test.txt", "w") as f:
        f.write("blabla")


if __name__ == "__main__":
    main()
