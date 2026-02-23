'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface FAQItemProps {
  question: string;
  answer: string;
}

export function FAQItem({ question, answer }: FAQItemProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="dl-faq-item">
      <button onClick={() => setIsOpen(!isOpen)} className="dl-faq-btn">
        <span className="dl-faq-question">{question}</span>
        {isOpen ? (
          <ChevronUp className="dl-faq-chevron-open" />
        ) : (
          <ChevronDown className="dl-faq-chevron-closed" />
        )}
      </button>
      {isOpen && (
        <div className="dl-faq-answer">{answer}</div>
      )}
    </div>
  );
}
