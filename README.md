# Example application for `file` and `object` storage

This [`flask`][flask] application is a demo for listing, creating, viewing, and
deleting files from the following storage types:

- **Local** storage: either by using container storage or a PersistentVolume (recommended)
- **S3** storage from AWS or other compatible service
  - S3 **NooBaa** object storage from OpenShift Container Storage

## Requirements

This application requires **OpenShift Container Storage** to be installed and
configured in the OCP cluster before deploying since it uses the following
storage classes provided by OCS:

- [`ocs-storagecluster-cephfs`](kustomization/overlays/pvc/pvc.yaml)
- [`openshift-storage.noobaa.io`](kustomization/overlays/s3-obc/obc.yaml)

For reference, [OpenShift Container Storage Operator][ocs-github] and
[Local Storage Operator][lso-github] provide the following storage classes on
the OCP cluster:

- `nfs-storage`
- `local-volume-class`
- `ocs-storagecluster-cephfs`
- `ocs-storagecluster-ceph-rbd`
- `ocs-storagecluster-ceph-rgw`
- `openshift-storage.noobaa.io`

## Install

There is a [`kustomization`](kustomization) folder that contains all the
resources needed to deploy the application in the three variants
(`ephemeral`, `pvc`, `s3`, and `s3-obc`).

If the deployment type is `s3`, be sure to fill the appropriate details on the
following files:

- [`kustomization/overlays/s3/configmap-s3.yaml`](kustomization/overlays/s3/configmap-s3.yaml)
- [`kustomization/overlays/s3/secret-s3.yaml`](kustomization/overlays/s3/secret-s3.yaml)

For the `s3-obc` there is no need to provide the `Secret` and `ConfigMap` since
they are created automatically by the `ObjectBucketClaim` resource.

There is also a [`Makefile`](Makefile) that aids in deploying and cleaning up resources,

### Deploying via `make`

```
$ make deploy [TYPE=<ephemeral|pvc|s3|s3-obc>]
```

### Deploying via `oc`

```
$ oc new project image-tool
$ oc kustomize kustomization/overlays/pvc/ | oc apply -f -
```

## Test

Depending on the type of deployment used you can access the web interface in
one of the following URLs:

| `TYPE`     | URL |
|:----------:|:----|
| `ephemeral`| <https://image-tool-ephemeral-image-tool.apps.ocp4.example.com/> |
| `pvc`      | <https://image-tool-pvc-image-tool.apps.ocp4.example.com/> |
| `s3`       | <https://image-tool-s3-image-tool.apps.ocp4.example.com/> |
| `s3-obc`   | <https://image-tool-s3-obc-image-tool.apps.ocp4.example.com/> |

The web page will tell you which storage type is being used.

## Cleanup

### Cleanup via `make`

```
$ make clean [TYPE=<ephemeral|pvc|s3|s3-obc>]
```

### Cleanup via `oc`

```
$ oc project default
$ oc delete project/image-tool
```

[flask]: https://flask.palletsprojects.com/
[lso-github]: https://github.com/openshift/local-storage-operator
[ocs-github]: https://github.com/openshift/ocs-operator
