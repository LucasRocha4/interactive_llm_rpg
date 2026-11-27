(() => {
  'use strict';

  const chat = document.getElementById('chat');
  const dado = document.getElementById('dado');
  const frase = document.getElementById('frase');
  const movimentoReduzido = window.matchMedia('(prefers-reduced-motion: reduce)');

  // Alterna os arquétipos dos cartões com uma transição curta.
  const classesVisuais = [
    { nome: 'Guerreiro', icone: '⚔' },
    { nome: 'Mago', icone: '✦' },
    { nome: 'Ladino', icone: '◈' },
    { nome: 'Arqueiro', icone: '➶' },
    { nome: 'Bardo', icone: '♫' }
  ];
  const cartoesClasse = Array.from(document.querySelectorAll('[data-classe-card]'));
  const indicesClasse = cartoesClasse.map((_, indice) => indice);
  let intervaloClasses;

  function trocarClasse(cartao, indiceAtual) {
    const proximoIndice = (indiceAtual + 3) % classesVisuais.length;
    const novaClasse = classesVisuais[proximoIndice];
    const nome = cartao.querySelector('[data-classe-nome]');
    const icone = cartao.querySelector('.classe-icone');

    if (movimentoReduzido.matches) {
      nome.textContent = novaClasse.nome;
      icone.textContent = novaClasse.icone;
      return proximoIndice;
    }

    cartao.classList.remove('classe-entrada');
    cartao.classList.add('trocando');
    window.setTimeout(() => {
      nome.textContent = novaClasse.nome;
      icone.textContent = novaClasse.icone;
      cartao.classList.remove('trocando');
      cartao.classList.add('classe-entrada');
      window.setTimeout(() => cartao.classList.remove('classe-entrada'), 500);
    }, 240);
    return proximoIndice;
  }

  function iniciarTrocaClasses() {
    window.clearInterval(intervaloClasses);
    if (document.hidden || movimentoReduzido.matches || cartoesClasse.length === 0) return;
    intervaloClasses = window.setInterval(() => {
      cartoesClasse.forEach((cartao, indice) => {
        indicesClasse[indice] = trocarClasse(cartao, indicesClasse[indice]);
      });
    }, 4200);
  }

  document.addEventListener('visibilitychange', iniciarTrocaClasses);
  movimentoReduzido.addEventListener('change', iniciarTrocaClasses);
  iniciarTrocaClasses();

  // Mantém os destinos que já estavam definidos no hub.
  document.querySelectorAll('[data-rota]').forEach((botao) => {
    botao.addEventListener('click', () => {
      window.location.href = botao.dataset.rota;
    });
  });

  const roteiro = [
    { tipo: 'ia', nome: 'Narrador', texto: 'A porta da masmorra range e revela um corredor iluminado por tochas. Ao fundo, um goblin afia uma adaga. O que vocês fazem?' },
    { tipo: 'p1', nome: 'Lyra', texto: 'Vou atacar o goblin pelas costas com minha espada!' },
    { tipo: 'ia', nome: 'Narrador', texto: 'Role um dado de ataque, Lyra.', dado: true },
    { tipo: 'ia', nome: 'Narrador', texto: 'Um 17! Sua lâmina corta o ar e o goblin cai antes de gritar.' },
    { tipo: 'p2', nome: 'Thorin', texto: 'Boa! Eu vou revistar o corpo atrás de pistas.' },
    { tipo: 'ia', nome: 'Narrador', texto: 'Entre as moedas, Thorin encontra um mapa rasgado com o símbolo de um dragão...' }
  ];

  const espera = (milissegundos) => new Promise((resolver) => window.setTimeout(resolver, milissegundos));

  async function rolarDado() {
    const numero = dado.querySelector('span');
    dado.classList.add('rolando');

    if (movimentoReduzido.matches) {
      numero.textContent = '17';
      dado.classList.remove('rolando');
      return;
    }

    for (let troca = 0; troca < 12; troca += 1) {
      numero.textContent = String(Math.ceil(Math.random() * 20));
      await espera(80);
    }
    dado.classList.remove('rolando');
    numero.textContent = '17';
  }

  function adicionarMensagem(mensagem) {
    const bloco = document.createElement('div');
    bloco.className = `msg ${mensagem.tipo}`;
    const nome = document.createElement('span');
    nome.className = 'nome';
    nome.textContent = mensagem.nome;
    bloco.append(nome, document.createTextNode(mensagem.texto));
    chat.appendChild(bloco);
  }

  async function tocarCena() {
    while (true) {
      chat.replaceChildren();
      for (const mensagem of roteiro) {
        adicionarMensagem(mensagem);
        if (mensagem.dado) {
          await espera(600);
          await rolarDado();
        }
        await espera(2200);
      }
      await espera(3000);
    }
  }

  const frases = [
    'A taverna está lotada hoje, aventureiro.',
    'Os dados estão aquecidos e a mesa está pronta.',
    'Dizem que um dragão foi visto nas montanhas ao norte.',
    'O bardo afina o alaúde enquanto o fogo estala na lareira.',
    'Uma carta lacrada com cera vermelha espera por você.',
    'A névoa cobre a estrada, mas a aventura não espera.',
    'Há uma vaga na mesa do canto. Aceita uma jornada?'
  ];
  let fraseAtual = Math.floor(Math.random() * frases.length);
  frase.textContent = frases[fraseAtual];

  const intervaloFrases = window.setInterval(() => {
    frase.classList.add('some');
    window.setTimeout(() => {
      let proximaFrase;
      do { proximaFrase = Math.floor(Math.random() * frases.length); }
      while (proximaFrase === fraseAtual);
      fraseAtual = proximaFrase;
      frase.textContent = frases[fraseAtual];
      frase.classList.remove('some');
    }, 600);
  }, 8000);

  // Partículas douradas no fundo.
  const canvas = document.getElementById('particulas');
  const contexto = canvas.getContext('2d');
  const telaPequena = window.matchMedia('(max-width: 600px)');
  let largura = 0;
  let altura = 0;
  let escala = 1;
  let particulas = [];
  let quadro = 0;

  function novaParticula(aleatoriaNaTela) {
    return {
      x: Math.random() * largura,
      y: aleatoriaNaTela ? Math.random() * altura : altura + 10,
      raio: Math.random() * 2 + .5,
      velocidade: Math.random() * .6 + .2,
      balanco: Math.random() * Math.PI * 2,
      brilho: Math.random() * .6 + .3
    };
  }

  function ajustarCanvas() {
    escala = Math.min(window.devicePixelRatio || 1, 1.5);
    largura = window.innerWidth;
    altura = window.innerHeight;
    canvas.width = Math.round(largura * escala);
    canvas.height = Math.round(altura * escala);
    contexto.setTransform(escala, 0, 0, escala, 0, 0);
    const total = telaPequena.matches ? 24 : 60;
    particulas = Array.from({ length: total }, () => novaParticula(true));
    pintarParticulas(false);
    iniciarParticulas();
  }

  function pintarParticulas(animar = true) {
    contexto.clearRect(0, 0, largura, altura);
    particulas.forEach((particula, indice) => {
      if (animar) {
        particula.y -= particula.velocidade;
        particula.balanco += .02;
        particula.x += Math.sin(particula.balanco) * .4;
        if (particula.y < -10) particulas[indice] = novaParticula(false);
      }
      contexto.beginPath();
      contexto.arc(particula.x, particula.y, particula.raio, 0, Math.PI * 2);
      contexto.fillStyle = `rgba(230, 199, 90, ${particula.brilho})`;
      contexto.shadowBlur = 8;
      contexto.shadowColor = '#c9a227';
      contexto.fill();
    });
    if (animar && !document.hidden) quadro = window.requestAnimationFrame(() => pintarParticulas(true));
  }

  function iniciarParticulas() {
    window.cancelAnimationFrame(quadro);
    if (!document.hidden && !movimentoReduzido.matches) {
      quadro = window.requestAnimationFrame(() => pintarParticulas(true));
    }
  }

  window.addEventListener('resize', ajustarCanvas, { passive: true });
  document.addEventListener('visibilitychange', iniciarParticulas);
  telaPequena.addEventListener('change', ajustarCanvas);
  movimentoReduzido.addEventListener('change', iniciarParticulas);

  ajustarCanvas();
  tocarCena();
})();
