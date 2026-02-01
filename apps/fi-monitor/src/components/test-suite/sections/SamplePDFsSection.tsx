import { FileText } from 'lucide-react';

interface SamplePDF {
  filename: string;
  title: string;
  description: string;
}

const SAMPLE_PDFS: SamplePDF[] = [
  {
    filename: 'hypertension_guide.pdf',
    title: '📊 Hypertension Guide',
    description: 'Clinical guidelines for hypertension management',
  },
  {
    filename: 'diabetes_guidelines.pdf',
    title: '🩸 Diabetes Guidelines',
    description: 'Evidence-based diabetes treatment protocols',
  },
  {
    filename: 'clinical_trials_guide.pdf',
    title: '🔬 Clinical Trials Guide',
    description: 'Best practices for clinical trial design',
  },
];

interface SamplePDFsSectionProps {
  onLoadSample: (filename: string) => void;
  isProcessing: boolean;
}

export function SamplePDFsSection({ onLoadSample, isProcessing }: SamplePDFsSectionProps) {
  return (
    <div className="sample-pdfs-section space-y-3">
      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Or try a sample PDF:</h4>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {SAMPLE_PDFS.map((pdf) => (
          <button
            key={pdf.filename}
            onClick={() => onLoadSample(pdf.filename)}
            disabled={isProcessing}
            className="flex flex-col items-start p-3 border dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 disabled:bg-gray-100 dark:disabled:bg-gray-700 disabled:cursor-not-allowed transition-colors text-left"
          >
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-4 h-4 text-blue-600" />
              <span className="font-medium text-sm">{pdf.title}</span>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400">{pdf.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
