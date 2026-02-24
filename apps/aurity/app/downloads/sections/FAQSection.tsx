import { FAQS } from '../constants';
import { FAQItem } from '../components/FAQItem';

export function FAQSection() {
  return (
    <section className="dl-faq-section">
      <div className="dl-section-container-narrow">
        <h2 className="dl-section-title-center">Preguntas Frecuentes</h2>
        <div className="dl-faq-container">
          {FAQS.map((faq, index) => (
            <FAQItem key={index} question={faq.question} answer={faq.answer} />
          ))}
        </div>
      </div>
    </section>
  );
}
