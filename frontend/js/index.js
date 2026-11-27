// ---------- 1. Dado grande que rola de verdade ----------
const dado = document.getElementById('dadoGrande');
const resultado = document.getElementById('dadoResultado');
let rolando = false;

function rolarDado() {
  if (rolando) return;
  rolando = true;
  resultado.textContent = '';
  dado.classList.remove('rolando');
  void dado.offsetWidth; // reinicia a animacao
  dado.classList.add('rolando');

  // Troca os numeros rapidamente enquanto gira
  const troca = setInterval(() => {
    dado.textContent = Math.floor(Math.random() * 20) + 1;
  }, 70);

  setTimeout(() => {
    clearInterval(troca);
    const final = Math.floor(Math.random() * 20) + 1;
    dado.textContent = final;
    if (final === 20) resultado.textContent = 'Acerto crítico! O destino sorri para você.';
    else if (final === 1) resultado.textContent = 'Falha crítica... o narrador está rindo.';
    else if (final >= 11) resultado.textContent = 'Boa rolagem! A aventura continua.';
    else resultado.textContent = 'Hmm... o destino não está do seu lado.';
    rolando = false;
  }, 1400);
}

dado.addEventListener('click', rolarDado);
setTimeout(rolarDado, 900); // rola sozinho ao carregar a pagina

// ---------- 2. Cena narrada interativa ----------
// Cada cena tem um texto e tres escolhas. Cada escolha gera um resultado.
const cenas = [
  {
    texto: 'A neblina cobre a estrada e, ao longe, uma luz trêmula na boca de uma caverna antiga. Você sente o peso da espada na cintura. Algo lá dentro respira. O que você faz?',
    escolhas: [
      { rotulo: 'Entrar na caverna', resultado: 'Você avança pela escuridão. O chão treme e dois olhos dourados se acendem diante de você. O narrador rola os dados... e a criatura recua, curiosa. Você ganhou alguns segundos.' },
      { rotulo: 'Apagar a tocha e escutar', resultado: 'No silêncio, você ouve passos pesados e uma voz rouca sussurrando seu nome. Os dados rolam: você não foi notado. Mas alguém sabe que você chegou.' },
      { rotulo: 'Voltar para a vila', resultado: 'Você dá as costas à caverna. A neblina se fecha atrás de você e, na vila, todas as portas estão trancadas. A história não ia deixar você fugir assim tão fácil.' }
    ]
  },
  {
    texto: 'O portão da cidade em ruínas range sozinho. Sobre o altar de pedra, um dado de ouro gira sem parar, sem que ninguém o toque. Cada volta faz as velas tremerem. O que você faz?',
    escolhas: [
      { rotulo: 'Pegar o dado de ouro', resultado: 'Seus dedos tocam o metal frio e as velas se apagam. Uma voz diz: "Agora você joga por mim". Os dados rolam, e o seu destino acaba de mudar de dono.' },
      { rotulo: 'Esperar o dado parar', resultado: 'O dado gira por uma eternidade e para no número 20. As paredes se abrem, revelando uma passagem secreta. A paciência foi recompensada.' },
      { rotulo: 'Quebrar o altar', resultado: 'A pedra racha e uma onda de luz roxa empurra você para trás. O dado desaparece, mas algo muito mais antigo acabou de acordar.' }
    ]
  },
  {
    texto: 'No porto, um barco sem tripulação balança nas ondas. Na proa há um mapa com o seu nome escrito, e a maré está subindo rápido. O que você faz?',
    escolhas: [
      { rotulo: 'Embarcar e seguir o mapa', resultado: 'As velas se enchem de vento sem que ninguém as toque. O narrador rola os dados e uma ilha surge no horizonte, exatamente onde o mapa apontava.' },
      { rotulo: 'Queimar o mapa', resultado: 'As chamas ficam azuis e o mapa se desfaz em cinzas que formam um novo desenho no ar. Você não escapa do destino, só o torna mais perigoso.' },
      { rotulo: 'Procurar quem deixou o barco', resultado: 'Na taverna, ninguém admite ter visto nada, mas um velho marinheiro desvia o olhar. Ele sabe de algo, e os dados dizem que ele está com medo.' }
    ]
  }
];

const alvo = document.getElementById('textoCena');
const caixaEscolhas = document.getElementById('escolhas');
let cenaAtual = 0;
let digitando = false;

// Escreve um texto letra por letra e chama 'depois' ao terminar
function digitar(texto, depois) {
  digitando = true;
  alvo.textContent = '';
  let i = 0;
  (function passo() {
    if (i < texto.length) {
      alvo.textContent += texto.charAt(i);
      i++;
      setTimeout(passo, 30);
    } else {
      digitando = false;
      if (depois) depois();
    }
  })();
}

function mostrarCena() {
  const cena = cenas[cenaAtual];
  caixaEscolhas.classList.remove('visivel');
  caixaEscolhas.innerHTML = '';
  digitar(cena.texto, () => {
    cena.escolhas.forEach(e => {
      const b = document.createElement('button');
      b.textContent = e.rotulo;
      b.addEventListener('click', () => escolher(e));
      caixaEscolhas.appendChild(b);
    });
    caixaEscolhas.classList.add('visivel');
  });
}

function escolher(escolha) {
  if (digitando) return;
  caixaEscolhas.classList.remove('visivel');
  caixaEscolhas.innerHTML = '';
  digitar(escolha.resultado, () => {
    // Botao para continuar para a proxima cena
    const b = document.createElement('button');
    b.textContent = 'Continuar a história';
    b.addEventListener('click', () => {
      cenaAtual = (cenaAtual + 1) % cenas.length;
      mostrarCena();
    });
    caixaEscolhas.appendChild(b);
    caixaEscolhas.classList.add('visivel');
  });
}

setTimeout(mostrarCena, 1500);

// ---------- 3. Fundo vivo: particulas brilhando ----------
const canvas = document.getElementById('particulas');
const ctx = canvas.getContext('2d');
let particulas = [];

function ajustar() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', ajustar);
ajustar();

for (let n = 0; n < 70; n++) {
  particulas.push({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    r: Math.random() * 2 + 0.5,
    vy: Math.random() * 0.4 + 0.1,
    fase: Math.random() * Math.PI * 2,
    cor: Math.random() > 0.5 ? '212,175,55' : '230,90,120'
  });
}

function animar() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  particulas.forEach(p => {
    p.y -= p.vy;
    p.fase += 0.03;
    if (p.y < -5) { p.y = canvas.height + 5; p.x = Math.random() * canvas.width; }
    const brilho = 0.35 + Math.sin(p.fase) * 0.3;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(' + p.cor + ',' + brilho + ')';
    ctx.shadowBlur = 12;
    ctx.shadowColor = 'rgba(' + p.cor + ',0.8)';
    ctx.fill();
  });
  requestAnimationFrame(animar);
}
animar();