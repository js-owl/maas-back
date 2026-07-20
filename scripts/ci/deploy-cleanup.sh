#!/usr/bin/env bash
# Best-effort image cleanup on deploy host. Source from deploy SSH scripts.
set +e

cleanup_app_images() {
  local repo="$1"
  local current_tag="${2:-}"

  if [ -z "$repo" ]; then
    echo "cleanup_app_images: missing repo argument"
    return 0
  fi

  local keep=""
  while IFS= read -r line; do
    keep="$keep $line"
  done < <(
    docker images "$repo" --format '{{.Tag}} {{.CreatedAt}}' 2>/dev/null \
      | grep -E '^(v|dev-v)[0-9]' \
      | sort -k2 -r \
      | head -2 \
      | awk '{print $1}'
  )

  for meta in latest dev-latest; do
    if docker images "$repo" --format '{{.Tag}}' 2>/dev/null | grep -qx "$meta"; then
      keep="$keep $meta"
    fi
  done

  if [ -n "$current_tag" ]; then
    keep="$keep $current_tag"
  fi

  while IFS= read -r tag; do
    [ -z "$tag" ] && continue
    if echo " $keep " | grep -q " ${tag} "; then
      continue
    fi
    echo "Removing ${repo}:${tag}"
    docker rmi "${repo}:${tag}" 2>/dev/null || true
  done < <(docker images "$repo" --format '{{.Tag}}' 2>/dev/null)

  docker image prune -f >/dev/null 2>&1 || true
}

build_runner_cleanup() {
  for img in "$@"; do
    [ -n "$img" ] && docker rmi "$img" 2>/dev/null || true
  done
  docker image prune -f >/dev/null 2>&1 || true
}
