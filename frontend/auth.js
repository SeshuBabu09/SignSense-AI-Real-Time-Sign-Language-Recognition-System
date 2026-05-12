const API = "http://127.0.0.1:5000";

function qs(id){ return document.getElementById(id); }

async function signup(){
  const email = qs("email").value.trim();
  const password = qs("password").value.trim();
  const domain = qs("domain").value;

  const msg = qs("msg");
  msg.className = "err";
  msg.innerText = "";

  if(!email || !password){
    msg.innerText = "Enter email and password";
    return;
  }

  const res = await fetch(`${API}/signup`, {
    method:"POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({email, password, domain})
  });

  const data = await res.json();
  if(data.ok){
    msg.className = "ok";
    msg.innerText = "Signup successful ✅ Now login";
    setTimeout(()=> window.location.href = "login.html", 900);
  } else {
    msg.innerText = data.message || "Signup failed";
  }
}

async function login(){
  const email = qs("email").value.trim();
  const password = qs("password").value.trim();

  const msg = qs("msg");
  msg.className = "err";
  msg.innerText = "";

  if(!email || !password){
    msg.innerText = "Enter email and password";
    return;
  }

  const res = await fetch(`${API}/login`, {
    method:"POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({email, password})
  });

  const data = await res.json();

  if(data.ok){
    const domain = data.domain;
    // redirect based on domain selection
    if(domain === "blind"){
      window.location.href = "blind.html";
    } else {
      window.location.href = "deaf.html";
    }
  } else {
    msg.innerText = data.message || "Login failed";
  }
}

// attach buttons if exists
if(document.getElementById("btnSignup")){
  document.getElementById("btnSignup").onclick = signup;
}
if(document.getElementById("btnLogin")){
  document.getElementById("btnLogin").onclick = login;
}
