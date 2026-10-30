ARG BASE
FROM node AS deps
FROM --platform=linux/amd64 alpine:latest AS tools
FROM ${BASE}
FROM registry.local:5000/team/app:1.4 AS app
FROM deps
