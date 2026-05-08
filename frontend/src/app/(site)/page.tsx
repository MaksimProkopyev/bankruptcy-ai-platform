import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Банкротство.AI — Списание долгов с помощью AI",
  description: "Банкротство физических лиц — законная процедура списания долгов. AI-скоринг за 2 минуты, от заявки до суда за 5 дней. Бесплатная консультация.",
  openGraph: {
    title: "Банкротство.AI — Списание долгов с помощью AI",
    description: "Банкротство физических лиц — законная процедура. Бесплатная оценка за 2 минуты.",
    url: "https://bankruptcy.ai",
    type: "website",
  },
};

const BENEFITS = [
  { icon: "bolt", title: "Заявка → суд за 5 дней", text: "AI собирает и проверяет документы в 5 раз быстрее" },
  { icon: "cpu", title: "AI-скоринг за 2 минуты", text: "Мгновенно определим перспективы вашего дела" },
  { icon: "eye", title: "Статус дела 24/7", text: "Личный кабинет с AI-ассистентом в любое время" },
  { icon: "wallet", title: "От 80 000 ₽ под ключ", text: "Прозрачная стоимость, никаких скрытых платежей" },
];

const STEPS = [
  { n: "01", title: "Бесплатная оценка", text: "AI-бот оценит ваши шансы за 2 минуты" },
  { n: "02", title: "Консультация юриста", text: "Подберём оптимальную стратегию" },
  { n: "03", title: "Сбор документов", text: "AI помогает собрать и проверить документы" },
  { n: "04", title: "Подача в суд", text: "Готовим и подаём заявление за вас" },
  { n: "05", title: "Списание долгов", text: "Суд завершает процедуру — долги списаны" },
];

const STATS = [
  { value: "1 200+", label: "дел завершено" },
  { value: "92%", label: "долгов списывается" },
  { value: "3–5 дней", label: "от заявки до суда" },
  { value: "24/7", label: "поддержка через AI" },
];

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 py-20 md:py-28">
        <div className="max-w-2xl">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 leading-tight tracking-tight">
            Списание долгов<br />
            <span className="text-accent">с помощью AI</span>
          </h1>
          <p className="mt-6 text-lg text-gray-600 leading-relaxed">
            Банкротство физических лиц — законная процедура списания долгов по ФЗ-127.
            Наш AI анализирует вашу ситуацию за 2 минуты и помогает пройти процедуру в 3 раза быстрее.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <button
              id="start-chat"
              className="px-8 py-3.5 bg-accent text-text-on-dark rounded-xl text-sm font-semibold hover:bg-accent-hover transition-colors shadow-lg shadow-accent/20"
            >
              Бесплатная оценка за 2 минуты
            </button>
            <a href="tel:+78001234567" className="px-8 py-3.5 bg-white border border-neutral text-text-body rounded-xl text-sm font-medium hover:bg-surface transition-colors">
              Позвонить юристу
            </a>
          </div>
        </div>
      </section>

      {/* Stats bar */}
      <section className="bg-primary-dark">
        <div className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-2xl md:text-3xl font-bold text-text-on-dark">{s.value}</p>
              <p className="text-text-on-dark-muted text-sm mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Benefits */}
      <section className="py-20 bg-surface">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-2xl md:text-3xl font-bold text-gray-900 text-center mb-12">
            Почему клиенты выбирают нас
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {BENEFITS.map((b) => (
              <div key={b.title} className="bg-white p-6 rounded-2xl border border-neutral">
                <div className="w-10 h-10 bg-primary-light rounded-xl flex items-center justify-center mb-4">
                  <div className="w-5 h-5 bg-primary rounded-sm" />
                </div>
                <h3 className="text-base font-semibold text-gray-900">{b.title}</h3>
                <p className="mt-2 text-sm text-text-muted leading-relaxed">{b.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20">
        <div className="max-w-3xl mx-auto px-6">
          <h2 className="text-2xl md:text-3xl font-bold text-gray-900 text-center mb-12">
            Как проходит процедура
          </h2>
          <div className="space-y-8">
            {STEPS.map((s) => (
              <div key={s.n} className="flex gap-5">
                <div className="w-12 h-12 bg-primary-light text-primary rounded-2xl flex items-center justify-center text-sm font-bold flex-shrink-0">
                  {s.n}
                </div>
                <div className="pt-1">
                  <h3 className="font-semibold text-gray-900 text-lg">{s.title}</h3>
                  <p className="mt-1 text-text-muted">{s.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-primary-dark py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-text-on-dark">
            Узнайте, подходит ли вам банкротство
          </h2>
          <p className="mt-4 text-text-on-dark-muted">
            AI-бот задаст 7 вопросов и мгновенно рассчитает стоимость и сроки. Бесплатно.
          </p>
          <button className="mt-8 px-8 py-3.5 bg-white text-primary rounded-xl text-sm font-semibold hover:bg-primary-light transition-colors">
            Начать бесплатную оценку
          </button>
        </div>
      </section>

      {/* SEO text */}
      <section className="py-16 bg-surface">
        <div className="max-w-3xl mx-auto px-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Банкротство физических лиц в России</h2>
          <div className="prose prose-gray prose-sm max-w-none text-text-body space-y-3">
            <p>Банкротство физических лиц — это законная процедура, предусмотренная Федеральным законом №127-ФЗ «О несостоятельности (банкротстве)». Она позволяет гражданам, не способным исполнить свои денежные обязательства, получить освобождение от долгов через судебную или внесудебную процедуру.</p>
            <p>Судебное банкротство применяется при долге от 500 000 рублей. Внесудебное банкротство через МФЦ доступно при долге от 25 000 до 1 000 000 рублей, если в отношении должника окончено исполнительное производство. Единственное жильё должника защищено законом и не подлежит изъятию.</p>
          </div>
        </div>
      </section>
    </>
  );
}
