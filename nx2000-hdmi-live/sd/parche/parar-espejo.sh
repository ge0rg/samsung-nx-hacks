#!/bin/sh
# Herramienta de Claude: para espejo.pl y espejo-mem.pl. "ps" de la cámara corta los nombres largos y
# "ps | grep espejo-mem" no los encontraba : se buscan en /proc/*/cmdline.
for d in /proc/[0-9]*; do
  c=$(tr '\0' ' ' < $d/cmdline 2>/dev/null)
  case "$c" in
    *espejo*.pl*) [ "${d#/proc/}" != "$$" ] && echo "parando ${d#/proc/}: $c" && kill ${d#/proc/} ;;
  esac
done
