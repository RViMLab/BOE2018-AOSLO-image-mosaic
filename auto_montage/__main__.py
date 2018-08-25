from . import auto_montage
import argparse


def main():
    """command line entry to detect"""
    parser = argparse.ArgumentParser(prog='auto_montage')
    parser.add_argument('-c', help='config path')
    args = parser.parse_args()
    auto_montage.main(args.c)


if __name__ == '__main__':
    main()