- debian update: version + changelog
- doc version update
- build and update the CHANGELOG.md
- MR
- create tag "vX.X.X"
- update the `stable` branch for the release (to update the `stable` version of readthedoc)
- pip release (this needs to be done before the docker step below)
  - clear `dist/`
  - download the artifacts of the `pip_pkg` step and unzip it in the root (it creates `dist/` with packages)
  - run `make pip_pkg_push`
- debian packages
  - wget `<pkg url>`
  - cd /var/www/html/repo/apt/debian/
  - reprepro -V --keepunreferencedfiles includedeb bookworm `<path to the .deb>`
- docker build:
  - clear pip caches
  - make docker_release_build APT_PROXY=http://192.168.1.24:3142/ PIP_INDEX_URL=http://192.168.3.3:5000/index/ PIP_TRUSTED_HOST=192.168.3.3
  - test
  - make docker_release_push
  - docker tag biolds/sosse:latest biolds/sosse:X.X.X
  - docker push biolds/sosse:X.X.X