// JS code for the Flask image tool

function load_image(url)
{
  var image = document.getElementById("image");
  image.src = "view" + "/" + url;
  console.log("View: " + image.src);
}

function upload_image()
{
  // Prepare upload elements
  file = document.getElementById("file")
  file_object = file.files[0];
  filename = file_object.name;
  var form_data = new FormData();
  form_data.append("file", file_object);

  var xhr = new XMLHttpRequest();
  xhr.open("POST", "upload", true);

  // Send the proper header information along with the request
  xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

  xhr.onreadystatechange = function()
  {
    // Call a function when the state changes.
    if (this.readyState === XMLHttpRequest.DONE && this.status === 200)
    {
      // Request finished. Do processing here.
      console.log("Upload: " + filename);
      // alert("File uploaded. Press the reload button.")
      setTimeout(
        function(){
          window.location.href("/");
        }, 1000
      );
    }
  }
  xhr.send(form_data);
}

function delete_image(filename)
{
  var xhr = new XMLHttpRequest();
  xhr.open("POST", "delete", true);

  // Send the proper header information along with the request
  xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

  xhr.onreadystatechange = function()
  {
    // Call a function when the state changes.
    if (this.readyState === XMLHttpRequest.DONE && this.status === 200)
    {
      // Request finished. Do processing here.
      console.log("Delete: " + filename);
      // alert("File Deleted. Press the reload button.")
      setTimeout(
        function(){
          window.location.reload(1);
        }, 1000
      );
    }
  }
  xhr.send("filename=" + filename);
}
