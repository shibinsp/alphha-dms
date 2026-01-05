/**
 * Local OCR Service using Tesseract.js
 * Provides offline OCR capabilities for document capture
 *
 * Note: Requires tesseract.js to be installed: npm install tesseract.js
 */

// Type definitions for tesseract.js (dynamic import)
type TesseractWorker = {
  recognize: (image: ImageSource) => Promise<{ data: RecognizeResult }>;
  terminate: () => Promise<void>;
};

type ImageSource = File | Blob | HTMLImageElement | HTMLCanvasElement | string;

interface RecognizeResult {
  text: string;
  confidence: number;
  words: Array<{
    text: string;
    confidence: number;
    bbox: { x0: number; y0: number; x1: number; y1: number };
  }>;
}

interface LoggerMessage {
  status: string;
  progress: number;
}

interface TesseractModule {
  createWorker: (
    lang: string,
    oem?: number,
    options?: { logger?: (m: LoggerMessage) => void }
  ) => Promise<TesseractWorker>;
}

export interface OCRResult {
  text: string;
  confidence: number;
  words: Array<{
    text: string;
    confidence: number;
    bbox: {
      x0: number;
      y0: number;
      x1: number;
      y1: number;
    };
  }>;
  processingTime: number;
}

export interface OCRProgress {
  status: string;
  progress: number;
}

export type ProgressCallback = (progress: OCRProgress) => void;

class LocalOCRService {
  private worker: TesseractWorker | null = null;
  private isInitialized = false;
  private initPromise: Promise<void> | null = null;
  private language = 'eng';
  private Tesseract: TesseractModule | null = null;

  /**
   * Initialize the Tesseract worker
   */
  async init(language: string = 'eng'): Promise<void> {
    if (this.isInitialized && this.language === language) return;
    if (this.initPromise) return this.initPromise;

    this.language = language;

    this.initPromise = (async () => {
      try {
        // Dynamic import tesseract.js
        if (!this.Tesseract) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const module = await import(/* webpackIgnore: true */ 'tesseract.js' as any);
          this.Tesseract = module.default || module;
        }

        // Terminate existing worker if any
        if (this.worker) {
          await this.worker.terminate();
        }

        // Create new worker
        if (!this.Tesseract) {
          throw new Error('Tesseract module not loaded');
        }
        this.worker = await this.Tesseract.createWorker(language, undefined, {
          logger: (m: LoggerMessage) => {
            if (m.status === 'recognizing text') {
              console.log(`OCR Progress: ${Math.round(m.progress * 100)}%`);
            }
          },
        });

        this.isInitialized = true;
        console.log('Local OCR initialized with language:', language);
      } catch (error) {
        console.error('Failed to initialize Tesseract:', error);
        throw error;
      }
    })();

    return this.initPromise;
  }

  /**
   * Process an image and extract text
   */
  async recognize(
    image: ImageSource,
    onProgress?: ProgressCallback
  ): Promise<OCRResult> {
    const startTime = Date.now();

    // Ensure worker is initialized
    await this.init();

    if (!this.worker || !this.Tesseract) {
      throw new Error('OCR worker not initialized');
    }

    try {
      // Create a custom worker for this request if progress callback is provided
      let worker = this.worker;

      if (onProgress) {
        worker = await this.Tesseract.createWorker(this.language, undefined, {
          logger: (m: LoggerMessage) => {
            onProgress({
              status: m.status,
              progress: m.progress,
            });
          },
        }) as TesseractWorker;
      }

      // Perform OCR
      const result = await worker.recognize(image);

      // Terminate temporary worker
      if (onProgress && worker !== this.worker) {
        await worker.terminate();
      }

      const processingTime = Date.now() - startTime;

      // Extract words with bounding boxes
      const words = result.data.words.map((word: RecognizeResult['words'][0]) => ({
        text: word.text,
        confidence: word.confidence,
        bbox: {
          x0: word.bbox.x0,
          y0: word.bbox.y0,
          x1: word.bbox.x1,
          y1: word.bbox.y1,
        },
      }));

      return {
        text: result.data.text,
        confidence: result.data.confidence,
        words,
        processingTime,
      };
    } catch (error) {
      console.error('OCR recognition failed:', error);
      throw error;
    }
  }

  /**
   * Process multiple images in batch
   */
  async recognizeBatch(
    images: Array<ImageSource>,
    onProgress?: (index: number, progress: OCRProgress) => void
  ): Promise<OCRResult[]> {
    const results: OCRResult[] = [];

    for (let i = 0; i < images.length; i++) {
      const result = await this.recognize(images[i], (progress) => {
        onProgress?.(i, progress);
      });
      results.push(result);
    }

    return results;
  }

  /**
   * Process a PDF file (page by page)
   * Note: This requires the PDF to be converted to images first
   */
  async recognizePDF(
    pdfPages: Array<HTMLCanvasElement>,
    onProgress?: (page: number, total: number, progress: OCRProgress) => void
  ): Promise<{
    pages: OCRResult[];
    fullText: string;
    avgConfidence: number;
    totalTime: number;
  }> {
    const startTime = Date.now();
    const results: OCRResult[] = [];
    let totalConfidence = 0;

    for (let i = 0; i < pdfPages.length; i++) {
      const result = await this.recognize(pdfPages[i], (progress) => {
        onProgress?.(i + 1, pdfPages.length, progress);
      });
      results.push(result);
      totalConfidence += result.confidence;
    }

    return {
      pages: results,
      fullText: results.map((r) => r.text).join('\n\n--- Page Break ---\n\n'),
      avgConfidence: totalConfidence / results.length,
      totalTime: Date.now() - startTime,
    };
  }

  /**
   * Extract text from a captured image (camera/scanner)
   */
  async processCapture(
    canvas: HTMLCanvasElement,
    options?: {
      preprocess?: boolean;
      onProgress?: ProgressCallback;
    }
  ): Promise<OCRResult> {
    let processedCanvas = canvas;

    // Apply preprocessing if requested
    if (options?.preprocess) {
      processedCanvas = this.preprocessImage(canvas);
    }

    return this.recognize(processedCanvas, options?.onProgress);
  }

  /**
   * Preprocess image for better OCR results
   */
  private preprocessImage(canvas: HTMLCanvasElement): HTMLCanvasElement {
    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;

    // Get image data
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    // Convert to grayscale and apply threshold
    for (let i = 0; i < data.length; i += 4) {
      const gray = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
      const threshold = gray > 128 ? 255 : 0;
      data[i] = threshold;
      data[i + 1] = threshold;
      data[i + 2] = threshold;
    }

    // Create new canvas with processed image
    const processedCanvas = document.createElement('canvas');
    processedCanvas.width = canvas.width;
    processedCanvas.height = canvas.height;
    const processedCtx = processedCanvas.getContext('2d');

    if (processedCtx) {
      processedCtx.putImageData(imageData, 0, 0);
    }

    return processedCanvas;
  }

  /**
   * Change the OCR language
   */
  async setLanguage(language: string): Promise<void> {
    if (this.language !== language) {
      await this.init(language);
    }
  }

  /**
   * Get available languages
   */
  getAvailableLanguages(): string[] {
    return [
      'eng', // English
      'ara', // Arabic
      'chi_sim', // Chinese Simplified
      'chi_tra', // Chinese Traditional
      'deu', // German
      'fra', // French
      'hin', // Hindi
      'jpn', // Japanese
      'kor', // Korean
      'por', // Portuguese
      'rus', // Russian
      'spa', // Spanish
    ];
  }

  /**
   * Terminate the worker
   */
  async terminate(): Promise<void> {
    if (this.worker) {
      await this.worker.terminate();
      this.worker = null;
      this.isInitialized = false;
      this.initPromise = null;
    }
  }

  /**
   * Check if OCR is supported in the current environment
   */
  isSupported(): boolean {
    return typeof Worker !== 'undefined' && typeof WebAssembly !== 'undefined';
  }
}

// Export singleton instance
export const localOCR = new LocalOCRService();
export default localOCR;
