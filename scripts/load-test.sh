#!/bin/sh
kubectl run load-test -n booktracker --rm -it --restart=Never --image=busybox:1.37 -- \
  sh -c "while true; do wget -q -O /dev/null http://backend:8000/api/books; done"
