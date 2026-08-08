/** Client-side deal photo helpers — keep uploads small enough to store as data URLs. */

const MAX_EDGE_PX = 1280;
const MAX_OUTPUT_BYTES = 350_000;
const JPEG_QUALITIES = [0.82, 0.72, 0.62, 0.5] as const;

function canvasToBlob(
  canvas: HTMLCanvasElement,
  type: string,
  quality: number,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob);
        else reject(new Error("Could not encode image"));
      },
      type,
      quality,
    );
  });
}

function readBlobAsDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") resolve(reader.result);
      else reject(new Error("Could not read image"));
    };
    reader.onerror = () => reject(new Error("Could not read image"));
    reader.readAsDataURL(blob);
  });
}

function loadImageElement(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not decode image"));
    };
    img.src = url;
  });
}

/**
 * Resize + JPEG-compress a deal photo so it can be stored in `deals.image_url`
 * as a data URL without blowing past API/DB practical limits.
 */
export async function compressDealImageFile(file: File): Promise<string> {
  const img = await loadImageElement(file);
  const scale = Math.min(1, MAX_EDGE_PX / Math.max(img.width, img.height));
  const width = Math.max(1, Math.round(img.width * scale));
  const height = Math.max(1, Math.round(img.height * scale));

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not prepare image canvas");
  ctx.drawImage(img, 0, 0, width, height);

  let best: Blob | null = null;
  for (const quality of JPEG_QUALITIES) {
    const blob = await canvasToBlob(canvas, "image/jpeg", quality);
    best = blob;
    if (blob.size <= MAX_OUTPUT_BYTES) break;
  }

  if (!best) throw new Error("Could not compress image");
  if (best.size > MAX_OUTPUT_BYTES * 1.5) {
    throw new Error(
      "Image is still too large after compression. Try a smaller photo or paste an https:// image URL.",
    );
  }

  return readBlobAsDataUrl(best);
}

export function isDealImageDataUrl(value: string): boolean {
  return /^data:image\/(png|jpe?g|webp|gif);base64,/i.test(value.trim());
}
