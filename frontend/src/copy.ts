import type { Verdict } from "./types";

export const resultTitles: Record<Verdict, string> = {
  "low-risk": "Leans human-made",
  review: "Mixed result",
  suspicious: "Leans AI-generated",
  inconclusive: "Not enough to tell",
};

export const resultCopy: Record<Verdict, string> = {
  "low-risk": "The available checks found few warning signs. That doesn’t prove the file is real.",
  review: "Some details look unusual. Editing, compression, or other changes could explain them. Check the source before drawing a conclusion.",
  suspicious: "The checks found details that deserve attention. Review the findings and compare the file with its original source.",
  inconclusive: "The available checks don’t give us enough information to say whether this file has been manipulated.",
};

export const findingCopy: Record<string, { title: string; description: string }> = {
  "generator-software": { title: "An AI tool is named in the file", description: "The saved software details mention an AI creation tool. These details can be changed, so they aren’t proof on their own." },
  "editing-software": { title: "An editing app is named in the file", description: "The file lists an editing app. Everyday changes like cropping or adjusting brightness can leave this detail too." },
  "metadata-absent": { title: "Few details about where it came from", description: "We couldn’t find the software or date details we look for. Websites and messaging apps often remove these when files are shared." },
  "low-texture-uniformity": { title: "The image looks unusually smooth", description: "We found very little variation in the image. Noise reduction, compression, or AI generation can all cause this." },
  "edge-discontinuity": { title: "Some edges change sharply", description: "There are abrupt changes between nearby pixels. Editing can cause this, but text and graphics can too." },
  "trailing-payload": { title: "Extra data follows the image", description: "This JPEG has extra bytes after the usual end of the image. That deserves a closer look, but it doesn’t prove the picture was changed." },
  "decode-failure": { title: "We couldn’t fully read this image", description: "The file looks like an image, but it couldn’t be opened correctly. It may be damaged or incomplete." },
  "mime-mismatch": { title: "The file type doesn’t match its label", description: "The upload describes one kind of file, but its contents suggest another. This can happen when a file is renamed or incorrectly exported." },
  "cryptographic-identity": { title: "Your file has a unique ID", description: "We created a fingerprint for this exact file. You can use it to check whether another copy is identical. It doesn’t tell us whether the content is real." },
  "high-entropy": { title: "The file’s data is unusually varied", description: "The file contains a wide mix of byte values. This may come from how it was compressed or stored; it isn’t proof of editing." },
  "container-only-analysis": { title: "Only basic file checks were run", description: "We checked file-level details. This version doesn’t yet examine video frames or listen for signs of an AI-generated voice." },
  "provenance-manifest": { title: "A possible source record was found", description: "We found a marker that may point to a record of how this file was created. We haven’t verified that record or its signature." },
  "provenance-unavailable": { title: "No source record was found", description: "We didn’t find a recognizable source-history marker in the part of the file we checked. Many real files don’t have one." },
};
