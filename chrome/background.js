chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (
    changeInfo.status === "complete" &&
    (tab.url.includes("music.youtube.com") || tab.url.includes("bilibili.com"))
  ) {
    chrome.scripting.executeScript({
      target: { tabId: tabId },
      function: initWebSocket,
    });
  }
});

function initWebSocket() {
  if (window.socket) {
    return;
  }

  window.socket = new WebSocket("ws://127.0.0.1:8765");

  window.socket.onclose = () => {
    socket = null;
    setTimeout(() => {
      initWebSocket();
    }, 5000);
  };

  window.socket.onerror = () => {
    window.socket.close();
  };
  window.sendSongDetails = () => {
    if (!window.socket || window.socket.readyState !== WebSocket.OPEN) {
      console.log("WebSocket is not open");
      return;
    }
    let songName,
      currentDuration,
      songArtistsAndAlbum = [];

    if (window.location.href.includes("music.youtube.com")) {
      const songDetailsParent = document.querySelector(
        ".content-info-wrapper.style-scope.ytmusic-player-bar"
      );

      songName = songDetailsParent.firstElementChild.innerHTML;
      currentDuration = document
        .getElementById("progress-bar")
        .querySelector(".slider-knob-inner.style-scope.tp-yt-paper-slider")
        .getAttribute("value");

      const songDetails = songDetailsParent.querySelectorAll(
        ".yt-simple-endpoint.style-scope.yt-formatted-string"
      );
      songDetails.forEach((elem) => {
        songArtistsAndAlbum.push(elem.innerHTML);
      });
    } else if (window.location.href.includes("bilibili.com")) {
      songName = document.querySelector("title").innerText;

      currentDuration = document.querySelector(
        ".bpx-player-ctrl-time-current"
      ).innerText;
      // change from 02:27 to 147

      currentDuration =
        parseInt(currentDuration.split(":")[0]) * 60 +
        parseInt(currentDuration.split(":")[1]);
    }

    if (window.socket && window.socket.readyState === WebSocket.OPEN) {
      window.socket.send(
        JSON.stringify({
          songName: songName,
          songArtistsAndAlbum: songArtistsAndAlbum.join(" "),
          currentDuration: currentDuration,
        })
      );
    }
  };

  if (!window.observingChanges) {
    window.observingChanges = true;
    const config = { attributes: true, childList: true, subtree: true };

    const observer = new MutationObserver(() => {
      window.sendSongDetails();
    });
    const attachObserver = () => {
      if (window.location.href.includes("music.youtube.com")) {
        const progressBar = document
          .getElementById("progress-bar")
          .querySelector(".slider-knob-inner.style-scope.tp-yt-paper-slider");
        if (progressBar) {
          observer.observe(progressBar, config);
        }
      }

      if (window.location.href.includes("bilibili.com")) {
        const currentTime = document.querySelector(
          ".bpx-player-ctrl-time-current"
        );
        if (currentTime) {
          observer.observe(currentTime, config);
        }
      }
    };

    // Initial attachment
    attachObserver();

    // Reattach observer if the DOM structure changes significantly
    const pageObserver = new MutationObserver(() => {
      observer.disconnect(); // Disconnect previous observers
      attachObserver(); // Reattach observers
    });

    // Observe significant changes in the body or other key elements
    pageObserver.observe(document.body, { childList: true, subtree: true });
  }
}
