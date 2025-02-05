const messages = [
    "Ești sigură că nu vrei?",
    "Sigur sigur??",
    "Glumești nu?",
    "Pui te rog...",
    "Gândește-te măcar puțin ;(",
    "Dacă spui nu chiar o să fiu trist....",
    "Foarte trist...",
    "Foarte foarte foarte trist...",
    "Gata, nu te mai intreb...",
    "Glumesc, spune daaaa te rogggg! ❤️"
];

let messageIndex = 0;

function handleNoClick() {
    const noButton = document.querySelector('.no-button');
    const yesButton = document.querySelector('.yes-button');
    noButton.textContent = messages[messageIndex];
    messageIndex = (messageIndex + 1) % messages.length;
    const currentSize = parseFloat(window.getComputedStyle(yesButton).fontSize);
    yesButton.style.fontSize = `${currentSize * 1.5}px`;
}

function handleYesClick() {
    window.location.href = "yes_page.html";
}
