from openapi_collector.cmd import get_parser


def test_get_parser():
    parser = get_parser()
    args = parser.parse_args(["--debug", "--interval=10"])
    assert args.debug
    assert 10 == args.interval
