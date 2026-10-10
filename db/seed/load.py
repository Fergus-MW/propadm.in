"""Seed the demo store at a local path or a gs://bucket/object shared store."""

import argparse
import os

from propadmin_core import open_store, seed_demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', default=os.getenv('PROPADMIN_DATA_PATH', '.data/state.json'))
    args = parser.parse_args()
    store = open_store(args.path)
    seed_demo(store)
    state = store.snapshot()
    print(f'Seeded {len(state["entities"])} entities into store {args.path}')


if __name__ == '__main__':
    main()
