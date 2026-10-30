#!/bin/sh
# Tag revisions like this:
# $ git tag -a -m "v0.2" v0.2
# Supports also pre-/post-/dev-releases and local version identifiers:
# $ git tag -a -m "v0.2rc3.post5.dev7+local.1" v0.2rc3.post5.dev7+local.1
# Enforcing canonical-like pattern with local version specifier:
#   N.N(.N)?[{a|b|rc}N][.postN][.devN][+{a..z0..9}(.{a..z0..9})*]
# See https://packaging.python.org/en/latest/specifications/version-specifiers
VERSION_IN=VERSION.in
VERSION_FILE=Exscript/version.py
REGEX_LOCALSPEC='(\+[a-z0-9]+(\.[a-z0-9]+)?)'
REGEX_CANONICAL='((0|[1-9][0-9]*)\.(0|[1-9][0-9]*))(\.(0|[1-9][0-9]*))?((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?'"${REGEX_LOCALSPEC}"'?'
REGEX_DESCRIBE='(\-([1-9][0-9]*)\-g[a-f0-9]+)'
ZERO_DESCRIBE='-0-g0000000'

# Check that we are actually in a git managed project.
if [ ! -e .git ] && [ -z "$1" ]; then
  echo >&2 Not a git repository.
  exit 1
fi

# Make sure that we have permission to modify the version file.
if [ -r "${VERSION_FILE}" ] && [ ! -w "${VERSION_FILE}" ]; then
  echo >&2 No permission to modify ${VERSION_FILE}.
  exit 1
fi

# If the --reset switch was given, reset the version number to 'DEVELOPMENT'.
if [ "$1" = "--reset" ]; then
  VERSION='DEVELOPMENT'
else
  # Use static version or get the version number from "git describe".
  if [ -n "$1" ]; then
    VERSION=$1
  else
    HEAD=$(git log -1 --pretty=format:%H HEAD)
    VERSION=$(git describe "${HEAD}" --tags --match "v[0-9]*")
  fi

  # Remove leading 'v' as it is not allowed for canonical versioning.
  VERSION=$(echo "${VERSION}" | sed -E 's/^v//')

  # Set implicit patch version to '.0' to always have a 'major.minor.patch' schema.
  VERSION=$(echo "${VERSION}" | sed -E 's/^([0-9]+\.[0-9]+)(\.?[a-z]|\+[a-z0-9]|$)/\1.0\2/')

  # Extract delta count of commits from possible "describe" suffix: -3-g454be62
  # Afterwards remove the "describe" suffix from version.
  DELTA=$(echo "${VERSION}" | (grep -Eio '('"${REGEX_DESCRIBE}"'$)' || echo "${ZERO_DESCRIBE}") | cut -f2 -d'-')
  VERSION=$(echo "${VERSION}" | sed -E 's/'"${REGEX_DESCRIBE}"'$//')

  # Validations.
  if [ -z "${VERSION}" ]; then
    echo >&2 No matching tag was found.
    exit 1
  elif ! (echo "${VERSION}" | grep -Eiq '^'"${REGEX_CANONICAL}"'$'); then
    echo >&2 "Version '${VERSION}' does not match canonical-like pattern 'N.N(.N)?[{a|b|rc}N][.postN][.devN][+{a..z0..9}(.{a..z0..9})*]'."
    echo >&2 "See also: https://packaging.python.org/en/latest/specifications/version-specifiers"
    exit 1
  fi

  # Extract local version specifier from version as his trailing number is optional.
  LOCALSPEC=$(echo "${VERSION}" | grep -Eio '('"${REGEX_LOCALSPEC}"'$)')
  VERSION=$(echo "${VERSION}" | sed -E 's/'"${REGEX_LOCALSPEC}"'$//')

  # Increment last number by commit delta.
  if [ "${LOCALSPEC}" ] && (echo "${LOCALSPEC}" | grep -Eiq '[0-9]$'); then
    INCREASED=$(( $(echo "${LOCALSPEC}" | grep -Eio '[0-9]+$') + DELTA ))
    LOCALSPEC=$(echo "${LOCALSPEC}" | sed -E 's/[0-9]+$/'"${INCREASED}"'/')
  else
    INCREASED=$(( $(echo "${VERSION}" | grep -Eio '[0-9]+$') + DELTA ))
    VERSION=$(echo "${VERSION}" | sed -E 's/[0-9]+$/'"${INCREASED}"'/')
  fi

  # Restore full version string.
  VERSION="${VERSION}${LOCALSPEC}"
fi

# If there is no version file, we are already done.
echo Version is "${VERSION}"
[ ! -r "${VERSION_FILE}" ] && exit 0

# Check whether the version file already contains this number,
# and only touch it if there is a change to avoid changing
# the timestamp.
VERSION_FILE_TMP=$(mktemp)
cat "${VERSION_IN}" | sed "s/@VERSION@/${VERSION}/g" > "${VERSION_FILE_TMP}"
if diff -q "${VERSION_FILE_TMP}" "${VERSION_FILE}"; then
  echo Version file unchanged.
  rm "${VERSION_FILE_TMP}"
  exit 0
fi

mv "${VERSION_FILE_TMP}" "${VERSION_FILE}"
echo Version file updated.
