#! /usr/bin/env python
import argparse

import updater


def _parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("paths", help="List of paths to run the updater in.", default=["."])

    return parser.parse_args()


def main():
    args = _parse_args()
    updater.run_updater(args.paths)


if __name__ == "__main__":
    main()
