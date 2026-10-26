/* BADS app helpers: service worker registration + "Add to Home Screen" hint. */
(function () {
  var root = document.documentElement.getAttribute("data-root") || "./";
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register(root + "sw.js", { scope: root }).catch(function () {});
    });
  }

  var standalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  var box = document.getElementById("install-hint");
  if (!box || standalone) return;
  var dismissed = false;
  try { dismissed = localStorage.getItem("bads-install-dismissed") === "1"; } catch (e) {}
  if (dismissed) return;

  var text = box.querySelector(".install-text");
  var btn = box.querySelector(".install-btn");
  var close = box.querySelector(".install-close");
  close.addEventListener("click", function () {
    box.hidden = true;
    try { localStorage.setItem("bads-install-dismissed", "1"); } catch (e) {}
  });

  var ua = navigator.userAgent || "";
  var isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  if (isIOS) {
    text.innerHTML = 'Get BADS as an app: tap <strong>Share</strong> <span aria-hidden="true">&#x2191;</span> in Safari, then <strong>Add to Home Screen</strong>.';
    btn.hidden = true;
    box.hidden = false;
    return;
  }

  var deferred = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    text.textContent = "Install BADS on your phone or desktop for one-tap access and offline reading.";
    btn.hidden = false;
    box.hidden = false;
  });
  btn.addEventListener("click", function () {
    if (!deferred) return;
    deferred.prompt();
    deferred.userChoice.finally(function () { deferred = null; box.hidden = true; });
  });
  window.addEventListener("appinstalled", function () { box.hidden = true; });
})();
