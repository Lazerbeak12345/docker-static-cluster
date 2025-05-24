# 5s-cluster

K8s is very abstract, whereas Docker's Cluster feature is just a step above docker compose.
This tries to be somewhere between, by building on Docker's Cluster

Docker's Cluster feature has a weakness, however, that it doesn't do high-availability very well when persistance is needed.

## How it works

It generates docker compose files, and runs `docker swarm` and related commands for you to do what you'd like.

In the config file, you indicate what apps you'd like, and what features they are composed of. Containers and volumes may both provide and use features.

## Status

I'm not yet using this yet myself.
