#!/usr/bin/env python3
import click

@click.group()
def main():
    pass

@main.command()
def generate():
    raise NotImplementedError(generate)

if __name__ == "__main__":
    main()
