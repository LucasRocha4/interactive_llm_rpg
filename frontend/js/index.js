(() => {
  'use strict';

  const movimentoReduzido = window.matchMedia('(prefers-reduced-motion: reduce)');

  // Revela os blocos conforme entram na tela.
  const blocos = document.querySelectorAll('.revelar');
  if ('IntersectionObserver' in window && !movimentoReduzido.matches) {
    const observador = new IntersectionObserver((entradas, atual) => {
      entradas.forEach((entrada) => {
        if (entrada.isIntersecting) {
          entrada.target.classList.add('visivel');
          atual.unobserve(entrada.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -35px 0px' });
    blocos.forEach((bloco) => observador.observe(bloco));
  } else {
    blocos.forEach((bloco) => bloco.classList.add('visivel'));
  }

  // Rola o dado com um resultado entre 1 e 20.
  const dado = document.getElementById('dadoGrande');
  const resultado = document.getElementById('dadoResultado');
  let rolando = false;

  dado.addEventListener('click', () => {
    if (rolando) return;
    rolando = true;
    dado.disabled = true;
    resultado.textContent = '';
    dado.classList.remove('rolando');
    void dado.offsetWidth;
    dado.classList.add('rolando');

    const duracao = movimentoReduzido.matches ? 0 : 1200;
    const troca = duracao ? window.setInterval(() => {
      dado.textContent = String(Math.floor(Math.random() * 20) + 1);
    }, 75) : null;

    window.setTimeout(() => {
      if (troca) window.clearInterval(troca);
      const final = Math.floor(Math.random() * 20) + 1;
      dado.textContent = String(final);
      if (final === 20) resultado.textContent = 'Acerto crítico! O destino sorri para você.';
      else if (final === 1) resultado.textContent = 'Falha crítica... o narrador está rindo.';
      else if (final >= 11) resultado.textContent = 'Boa rolagem! A aventura continua.';
      else resultado.textContent = 'Hmm... o destino não está do seu lado.';
      rolando = false;
      dado.disabled = false;
    }, duracao);
  });

  // Cenas de demonstração e suas escolhas.
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
  const paragrafoCena = alvo.closest('[aria-live]');
  const caixaEscolhas = document.getElementById('escolhas');
  let cenaAtual = 0;
  let digitando = false;
  let temporizadorTexto = 0;

  // Digita a narração e libera escolhas ao terminar.
  function digitar(texto, depois) {
    window.clearTimeout(temporizadorTexto);
    digitando = true;
    paragrafoCena.setAttribute('aria-live', 'off');
    alvo.textContent = '';

    if (movimentoReduzido.matches) {
      alvo.textContent = texto;
      concluirDigitacao(depois);
      return;
    }

    let indice = 0;
    function passo() {
      if (indice < texto.length) {
        alvo.textContent += texto.charAt(indice);
        indice += 1;
        temporizadorTexto = window.setTimeout(passo, 24);
      } else {
        concluirDigitacao(depois);
      }
    }
    passo();
  }

  function concluirDigitacao(depois) {
    digitando = false;
    paragrafoCena.setAttribute('aria-live', 'polite');
    if (depois) depois();
  }

  function mostrarCena() {
    const cena = cenas[cenaAtual];
    caixaEscolhas.classList.remove('visivel');
    caixaEscolhas.replaceChildren();
    digitar(cena.texto, () => {
      cena.escolhas.forEach((escolha) => {
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.textContent = escolha.rotulo;
        botao.addEventListener('click', () => escolher(escolha));
        caixaEscolhas.appendChild(botao);
      });
      caixaEscolhas.classList.add('visivel');
    });
  }

  function escolher(escolha) {
    if (digitando) return;
    caixaEscolhas.classList.remove('visivel');
    caixaEscolhas.replaceChildren();
    digitar(escolha.resultado, () => {
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.textContent = 'Continuar a história';
      botao.addEventListener('click', () => {
        cenaAtual = (cenaAtual + 1) % cenas.length;
        mostrarCena();
      });
      caixaEscolhas.appendChild(botao);
      caixaEscolhas.classList.add('visivel');
    });
  }

  mostrarCena();

  // Mantém poucas partículas e suspende o desenho fora da aba ativa.
  const canvas = document.getElementById('particulas');
  const contexto = canvas.getContext('2d');
  const telaPequena = window.matchMedia('(max-width: 600px)');
  let particulas = [];
  let quadro = 0;
  let largura = 0;
  let altura = 0;
  let escala = 1;

  function criarParticulas() {
    const quantidade = telaPequena.matches ? 22 : 48;
    particulas = Array.from({ length: quantidade }, () => ({
      x: Math.random() * largura,
      y: Math.random() * altura,
      raio: Math.random() * 1.5 + 0.45,
      velocidade: Math.random() * 0.24 + 0.08,
      fase: Math.random() * Math.PI * 2,
      cor: Math.random() > 0.62 ? '232,160,176' : '212,175,55'
    }));
  }

  function ajustarCanvas() {
    escala = Math.min(window.devicePixelRatio || 1, 1.5);
    largura = window.innerWidth;
    altura = window.innerHeight;
    canvas.width = Math.round(largura * escala);
    canvas.height = Math.round(altura * escala);
    contexto.setTransform(escala, 0, 0, escala, 0, 0);
    criarParticulas();
    desenhar(false);
  }

  function desenhar(animado = true) {
    contexto.clearRect(0, 0, largura, altura);
    particulas.forEach((particula) => {
      if (animado) {
        particula.y -= particula.velocidade;
        particula.fase += 0.018;
        if (particula.y < -4) {
          particula.y = altura + 4;
          particula.x = Math.random() * largura;
        }
      }
      const brilho = 0.18 + (Math.sin(particula.fase) + 1) * 0.13;
      contexto.beginPath();
      contexto.arc(particula.x, particula.y, particula.raio, 0, Math.PI * 2);
      contexto.fillStyle = `rgba(${particula.cor}, ${brilho})`;
      contexto.fill();
    });
    if (animado) quadro = window.requestAnimationFrame(() => desenhar(true));
  }

  function atualizarAnimacao() {
    window.cancelAnimationFrame(quadro);
    if (!document.hidden && !movimentoReduzido.matches) desenhar(true);
  }

  window.addEventListener('resize', ajustarCanvas, { passive: true });
  document.addEventListener('visibilitychange', atualizarAnimacao);
  telaPequena.addEventListener('change', ajustarCanvas);
  movimentoReduzido.addEventListener('change', atualizarAnimacao);
  ajustarCanvas();
  atualizarAnimacao();
})();
