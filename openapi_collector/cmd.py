import argparse


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', '-d', help='Debug mode: print more information', action='store_true')
    parser.add_argument('--interval', type=int, help='Loop interval (default: 30s)', default=30)
    return parser
