#docker image prune --filter label=massdns
#docker build --no-cache --progress=plain -t massdns:latest .
docker build --progress=plain -t vowifi-geoblocking-resolve-domains:latest .
docker run --rm -it --volume=./results/:/vowifi-geoblocking-resolve-domains/results/ --volume=./resources/:/vowifi-geoblocking-resolve-domains/resources/ vowifi-geoblocking-resolve-domains
