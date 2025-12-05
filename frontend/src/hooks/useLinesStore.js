import { create } from "zustand";

export const useLinesStore = create((set, get) => ({
  lines: {},
  images: [],

  setImages: (imageList) => {
    set({ images: imageList });
  },

  loadLines: (linesData) => {
    set({ lines: linesData });
  },

  addLine: (filename, x) => {
    set((state) => ({
      lines: {
        ...state.lines,
        [filename]: [...(state.lines[filename] || []), x],
      },
    }));
  },

  removeLine: (filename) => {
    set((state) => {
      const currentLines = state.lines[filename] || [];
      if (currentLines.length === 0) return state;

      return {
        lines: {
          ...state.lines,
          [filename]: currentLines.slice(0, -1),
        },
      };
    });
  },

  updateLine: (filename, index, newX) => {
    set((state) => {
      const currentLines = [...(state.lines[filename] || [])];
      currentLines[index] = newX;

      return {
        lines: {
          ...state.lines,
          [filename]: currentLines,
        },
      };
    });
  },

  replicateLines: (sourceFilename, onlyEmpty) => {
    set((state) => {
      const sourceLines = state.lines[sourceFilename] || [];
      if (sourceLines.length === 0) return state;

      const newLines = { ...state.lines };

      state.images.forEach((filename) => {
        if (filename === sourceFilename) return;

        if (onlyEmpty) {
          if (!newLines[filename] || newLines[filename].length === 0) {
            newLines[filename] = [...sourceLines];
          }
        } else {
          newLines[filename] = [...sourceLines];
        }
      });

      return { lines: newLines };
    });
  },

  exportJSON: () => {
    return get().lines;
  },
}));
