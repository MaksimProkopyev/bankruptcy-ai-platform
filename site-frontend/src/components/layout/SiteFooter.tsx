import Link from "next/link";

export default function SiteFooter() {
  return (
    <footer className="bg-primary-dark text-text-on-dark-muted">
      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
          {/* Brand */}
          <div>
            <Link href="/" className="text-xl font-bold text-text-on-dark font-heading">
              Банкротство.AI
            </Link>
            <p className="mt-3 text-sm text-text-on-dark-muted leading-relaxed">
              AI-first юридическая компания по банкротству физических лиц.
              Списание долгов законно и прозрачно.
            </p>
          </div>

          {/* Services */}
          <div>
            <h4 className="text-sm font-semibold text-text-on-dark mb-4">Услуги</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/uslugi" className="hover:text-text-on-dark transition-colors">Банкротство физлиц</Link></li>
              <li><Link href="/uslugi#vnsudebnoe" className="hover:text-text-on-dark transition-colors">Внесудебное банкротство</Link></li>
              <li><Link href="/uslugi#restrukturizaciya" className="hover:text-text-on-dark transition-colors">Реструктуризация долгов</Link></li>
              <li><Link href="/faq" className="hover:text-text-on-dark transition-colors">Частые вопросы</Link></li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="text-sm font-semibold text-text-on-dark mb-4">Компания</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/o-kompanii" className="hover:text-text-on-dark transition-colors">О нас</Link></li>
              <li><Link href="/blog" className="hover:text-text-on-dark transition-colors">Блог</Link></li>
              <li><Link href="/kontakty" className="hover:text-text-on-dark transition-colors">Контакты</Link></li>
              <li><Link href="/lk/login" className="hover:text-text-on-dark transition-colors">Личный кабинет</Link></li>
            </ul>
          </div>

          {/* Contacts */}
          <div>
            <h4 className="text-sm font-semibold text-text-on-dark mb-4">Контакты</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="tel:+78001234567" className="hover:text-text-on-dark transition-colors">
                  8 800 123-45-67
                </a>
                <span className="text-text-on-dark-muted text-xs block">Бесплатно по России</span>
              </li>
              <li>
                <a href="mailto:info@bankruptcy.ai" className="hover:text-text-on-dark transition-colors">
                  info@bankruptcy.ai
                </a>
              </li>
              <li className="text-text-on-dark-muted text-xs">Пн–Пт: 9:00–19:00 МСК</li>
            </ul>
          </div>
        </div>

        <div className="border-t border-border-dark mt-12 pt-8 flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-text-on-dark-muted">
            &copy; {new Date().getFullYear()} Банкротство.AI. Все права защищены.
          </p>
          <div className="flex gap-6 text-xs text-text-on-dark-muted">
            <Link href="/privacy" className="hover:text-text-on-dark">Политика конфиденциальности</Link>
            <Link href="/terms" className="hover:text-text-on-dark">Пользовательское соглашение</Link>
            <Link href="/oferta" className="hover:text-text-on-dark">Оферта</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
