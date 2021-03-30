#!/usr/bin/env python3
# Python code for the Flask image tool

# https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/#uploading-files
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
# https://blog.oddbit.com/post/2021-02-10-object-storage-with-openshift/

"""
Simple flask application to list, upload, view and delete images
"""

# TODO: Refactor code to separate file and S3 tasks
# TODO: Add /health and /ready checks with JSON output

import os
import sys
import uuid
import shutil
import hashlib
import boto3
import flask
from werkzeug.utils import secure_filename

# Initialize flask settings
app = flask.Flask(__name__)
app.logger = flask.logging.create_logger(app)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", str(uuid.uuid4()))
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "/tmp/storage")
app.config["MAX_CONTENT_LENGTH"] = 1024 ** 2
app.config["ALLOWED_EXTENSIONS"] = {"bmp", "gif", "jpg", "jpeg", "png", "tiff", "svg"}

# AWS_DEFAULT_REGION may be empty in NooBaa
app.config["AWS_DEFAULT_REGION"] = os.environ.get("AWS_DEFAULT_REGION", None)
app.config["AWS_ACCESS_KEY_ID"] = os.environ.get("AWS_ACCESS_KEY_ID", None)
app.config["AWS_SECRET_ACCESS_KEY"] = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
app.config["BUCKET_NAME"] = os.environ.get("BUCKET_NAME", None)
app.config["BUCKET_HOST"] = os.environ.get("BUCKET_HOST", None)
app.config["BUCKET_PORT"] = os.environ.get("BUCKET_PORT", None)
app.config["BUCKET_SCHEMA"] = "http" if app.config["BUCKET_PORT"] == "80" else "https"
app.config["ENDPOINT_URL"] = "{}://{}".format(
    app.config["BUCKET_SCHEMA"], app.config["BUCKET_HOST"]
)

# Check if S3 is enabled via environment variables
if None in [
    app.config["AWS_ACCESS_KEY_ID"],
    app.config["AWS_SECRET_ACCESS_KEY"],
    app.config["BUCKET_NAME"],
]:
    S3_SUPPORTED = False
    # Check if we are using a mounted volume from a PVC or ephemeral storage
    if os.path.ismount(app.config["UPLOAD_FOLDER"]):
        app.config["DEPLOYMENT_TYPE"] = "pvc"
    else:
        app.config["DEPLOYMENT_TYPE"] = "ephemeral"

else:
    S3_SUPPORTED = True
    app.config["DEPLOYMENT_TYPE"] = "S3"
    # Check if NooBaa is enabled via environment variables
    if None in [
        app.config["BUCKET_HOST"],
        app.config["BUCKET_PORT"],
    ]:
        NOOBAA_ENABLED = False
        S3 = boto3.client("s3")
    else:
        NOOBAA_ENABLED = True
        S3 = boto3.client("s3", endpoint_url=app.config["ENDPOINT_URL"])

app.logger.info("Serving files from {} storage".format(str(app.config["DEPLOYMENT_TYPE"]).upper()))

if not os.path.isdir(app.config["UPLOAD_FOLDER"]):
    app.logger.info("UPLOAD_FOLDER does not exist.")
    os.makedirs(app.config["UPLOAD_FOLDER"])


def allowed_file(filename):
    """
    Check if the filename matches the ALLOWED_EXTENSIONS list
    """
    allowed = False
    if "." in filename:
        extension = filename.rsplit(".", 1)[1].lower()
        if extension in app.config["ALLOWED_EXTENSIONS"]:
            allowed = True
    return allowed


def get_hash(data):
    """
    Get a checksum for the input data
    """
    md5 = hashlib.md5()
    md5.update(data)
    return md5.hexdigest()


@app.route("/favicon.ico", methods=["GET"])
def favicon():
    """
    Return an empty favicon
    """
    return ""


@app.route("/", methods=["GET"])
def index():
    """
    Display the root of the website
    """
    template = ""
    if S3_SUPPORTED:
        app.logger.info("S3: Listing bucket")
        listing = list_s3_objects()
        template = flask.render_template(
            "index.html.j2",
            items=listing,
            deployment_type=app.config["DEPLOYMENT_TYPE"],
            bucket=app.config["BUCKET_NAME"],
            endpoint=app.config["ENDPOINT_URL"],
        )
    else:
        app.logger.info("FILE: Listing directory")
        listing = os.listdir(app.config["UPLOAD_FOLDER"])
        template = flask.render_template(
            "index.html.j2",
            items=listing,
            deployment_type=app.config["DEPLOYMENT_TYPE"],
            folder=app.config["UPLOAD_FOLDER"],
        )
    return template


def list_s3_objects():
    """
    List objects present in the configured S3 bucket
    """
    listing = []
    try:
        response = S3.list_objects(
            Bucket=app.config["BUCKET_NAME"],
        )
        for item in response.get("Contents", []):
            listing.append(item["Key"])
    except Exception as e:
        app.logger.error(
            "S3: Unable to list objects in bucket: {}".format(app.config["BUCKET_NAME"])
        )
        app.logger.debug(e)
    return listing


@app.route("/view/<filename>", methods=["GET"])
def view(filename):
    """
    Return a given file from the storage
    """
    filename = secure_filename(filename)
    ext = filename.rsplit(".", 1)[1].lower()

    if S3_SUPPORTED and allowed_file(filename):
        content = ""
        try:
            app.logger.info("S3: Read: {}".format(filename))
            content = flask.Response(
                view_object(filename).read(), mimetype="image/{}".format(ext)
            )
        except Exception as e:
            app.logger.debug(e)
            return flask.redirect(flask.url_for("index"))
        return content
    else:
        full_filename = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        app.logger.info("FILE: Read: {}".format(full_filename))

        if allowed_file(full_filename) and os.path.isfile(full_filename):
            # Check file hash before returning it
            try:
                with open(full_filename, "rb") as existing_file:
                    checksum = get_hash(existing_file.read())
                    if checksum == filename.split(".")[0].lower():
                        response = flask.send_from_directory(
                            app.config["UPLOAD_FOLDER"], filename
                        )
                        response.mimetype = "image/{}".format(ext)
                        return response
            except Exception as e:
                app.logger.error(
                    "Can't open file for reading: {}".format(full_filename)
                )
                app.logger.debug(e)

    return flask.redirect(flask.url_for("index"))


def view_object(filename):
    """
    Retrieve and return an object from the S3 bucket
    """
    response = {}
    try:
        app.logger.info("S3: Read: {}".format(filename))
        response = S3.get_object(
            Bucket=app.config["BUCKET_NAME"],
            Key=filename,
        )
    except Exception as e:
        response["Body"] = ""
        app.logger.error("S3: Unable to get object: {}".format(filename))
        app.logger.debug(e)
    return response["Body"]


@app.route("/upload", methods=["GET", "POST"])
def upload():
    """
    Upload a file
    """
    if flask.request.method == "GET":
        return flask.redirect(flask.url_for("index"))
    # check if the post request has the file part
    if "file" not in flask.request.files:
        app.logger.error("No file part")
        return flask.redirect(flask.request.url)
    file = flask.request.files["file"]
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == "":
        app.logger.info("No file selected for upload")
        return flask.redirect(flask.url_for("index"))
    # Save the file
    if file and allowed_file(file.filename):
        try:
            app.logger.info("Trying to upload file")
            # Save the file with a temporary UUID name
            filename = secure_filename(file.filename)
            ext = filename.rsplit(".", 1)[1].lower()
            filename = str(uuid.uuid4())
            full_filename = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(full_filename)
            # Rename file with the MD5 hash and the extension
            with open(full_filename, "rb") as uploaded_file:
                checksum = get_hash(uploaded_file.read())
                new_filename = "{}.{}".format(checksum, ext)
            if S3_SUPPORTED:
                with open(full_filename, "rb") as uploaded_file:
                    upload_s3_object(new_filename, uploaded_file.read())
                    app.logger.info("S3: Write: {}".format(new_filename))
            else:
                new_filename = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
                shutil.move(full_filename, new_filename)
                app.logger.info("FILE: Write: {}".format(new_filename))
        except Exception as e:
            app.logger.error("Can't open file for reading: {}".format(full_filename))
            app.logger.debug(e)

    app.logger.info("File uploaded")
    return flask.redirect(flask.url_for("index"))


def upload_s3_object(file_name, file_data):
    """
    Upload an object to an S3 bucket
    """
    try:
        app.logger.info("S3: Put object: {}".format(file_name))
        S3.put_object(
            Bucket=app.config["BUCKET_NAME"],
            Key=file_name,
            Body=file_data,
        )
    except Exception as e:
        app.logger.error("S3: Unable to upload object: {}".format(file_name))
        app.logger.debug(e)


@app.route("/delete", methods=["GET", "POST"])
def delete():
    """
    Delete the file if it exists and the hash matches
    """
    if flask.request.method == "GET":
        return flask.redirect(flask.url_for("index"))

    form = flask.request.form.to_dict()
    filename = secure_filename(form.get("filename", None))

    if S3_SUPPORTED:
        delete_s3_object(filename)
    else:
        delete_file(filename)

    return flask.redirect(flask.url_for("index"))


def delete_file(filename):
    """
    Delete file from FILE storage
    """
    full_filename = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    try:
        if allowed_file(full_filename) and os.path.isfile(full_filename):
            # Check file hash before deleting
            with open(full_filename, "rb") as uploaded_file:
                checksum = get_hash(uploaded_file.read())
                if checksum == filename.split(".")[0].lower():
                    # Delete the file
                    app.logger.info("FILE: Delete: {}".format(filename))
                    os.remove(full_filename)
    except Exception as e:
        app.logger.error("FILE: Unable to delete file: {}".format(filename))
        app.logger.debug(e)


def delete_s3_object(filename):
    """
    Delete object from S3 bucket
    """
    try:
        app.logger.info("S3: Delete: {}".format(filename))
        S3.delete_object(
            Bucket=app.config["BUCKET_NAME"],
            Key=filename,
        )
    except Exception as e:
        app.logger.error("S3: Unable to delete object: {}".format(filename))
        app.logger.debug(e)


if __name__ == "__main__":
    app.debug = True
    app.run()
