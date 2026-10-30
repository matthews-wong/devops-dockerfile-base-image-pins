.PHONY: test validate

test:
	python3 -m unittest discover -s tests

# the pinned example must pass; the loose one must fail even without --strict
validate: test
	python3 pinaudit.py --strict examples/pinned.Dockerfile
	! python3 pinaudit.py examples/loose.Dockerfile > /dev/null
