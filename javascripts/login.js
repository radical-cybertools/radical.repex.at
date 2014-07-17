var count = 2;

var unArray = ["Antons", "George", "Sarah", "Michael"];  
var pwArray = ["tuscan", "Password2", "Password3", "Password4"]; 

function validate() {

  var un = document.myform.username.value;
  var pw = document.myform.pword.value;
  var valid = false;

  for (var i=0; i <unArray.length; i++) {
    if ((un == unArray[i]) && (pw == pwArray[i])) {
      valid = true;
      break;
    }
  }

  if (valid) {
    //alert ("Login was successful");
    window.location = "/RepEx/logged/";
    sessionStorage.setItem("username", un);
    sessionStorage.setItem("password", pw);
    return false;
  }

  var t = " tries";
  if (count == 1) {t = " try"}

  if (count >= 1) {
    alert ("Invalid username and/or password.  You have " + count + t + " left.");
    document.myform.username.value = "";
    document.myform.pword.value = "";
    setTimeout("document.myform.username.focus()", 25);
    setTimeout("document.myform.username.select()", 25);
    count --;
  } else {
    alert ("Still incorrect! You have no more tries left!");
    document.myform.username.value = "No more tries allowed!";
    document.myform.pword.value = "";
    document.myform.username.disabled = true;
    document.myform.pword.disabled = true;
    return false;
  }
}

function check(){

  var un = sessionStorage.getItem("username");
  var pw = sessionStorage.getItem("password");
  var valid = false;

  for (var i=0; i <unArray.length; i++) {
    if ((un == unArray[i]) && (pw == pwArray[i])) {
      valid = true;
      break;
    }
  }

  if (valid) {
     //alert ("Login was successful");    
  } else {
     alert ("You don't have permission to access this part of the website!");
     window.location = "http://www.google.com";
  }
}

function clear(){
  //alert ("Clear!"); 
  sessionStorage.setItem("username", "");
  sessionStorage.setItem("password", ""); 
}  