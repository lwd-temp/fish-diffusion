import json

import numpy as np
import torch
from torch.utils.data import Dataset

from fish_audio_preprocess.utils.file import list_files
from pathlib import Path
from .builder import DATASETS


@DATASETS.register_module()
class AudioFolderDataset(Dataset):
    def __init__(self, path="dataset", speaker_mapping="dataset/speakers.json"):
        self.wav_paths = list_files(path, {".wav"}, recursive=True)
        self.dataset_path = Path(path)

        self.speaker_map = json.loads(Path(speaker_mapping).read_text())

    def __len__(self):
        return len(self.wav_paths)

    def __getitem__(self, idx):
        wav_path: Path = self.wav_paths[idx]

        speaker_id = 0
        wav_path = str(wav_path)

        mel_path = wav_path + ".mel.npy"
        mel = np.load(mel_path).T

        c_path = wav_path + f".soft.npy"
        c = np.load(c_path).T
        pitch_path = wav_path + ".f0.npy"
        pitch = np.load(pitch_path)

        sample = {
            "path": wav_path,
            "speaker": speaker_id,
            "content": c,
            "mel": mel,
            "pitch": pitch,
        }

        return sample

    def parse_wav_paths(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            wavpaths = []
            for line in f.readlines():
                wavpath = line.strip("\n")
                wavpaths.append(Path(wavpath))
            return wavpaths

    @staticmethod
    def collate_fn(data):
        info = {
            "paths": [d["path"] for d in data],
            "speakers": torch.LongTensor([d["speaker"] for d in data]),
        }

        # Create contents and padding
        contents = [torch.from_numpy(d["content"]) for d in data]
        content_lens = torch.LongTensor([c.shape[0] for c in contents])
        max_content_len = torch.max(content_lens)
        contents = torch.stack(
            [
                torch.nn.functional.pad(c, (0, 0, 0, max_content_len - c.shape[0]))
                for c in contents
            ]
        )

        info["contents"] = contents
        info["content_lens"] = content_lens
        info["max_content_len"] = max_content_len

        # Create mels and padding
        mels = [torch.from_numpy(d["mel"]) for d in data]
        mel_lens = torch.LongTensor([mel.shape[0] for mel in mels])
        max_mel_len = torch.max(mel_lens)
        mels = torch.stack(
            [
                torch.nn.functional.pad(mel, (0, 0, 0, max_mel_len - mel.shape[0]))
                for mel in mels
            ]
        )

        info["mels"] = mels
        info["mel_lens"] = mel_lens
        info["max_mel_len"] = max_mel_len

        # Create pitches and padding
        pitches = [torch.from_numpy(d["pitch"]) for d in data]
        pitch_lens = torch.LongTensor([pitch.shape[0] for pitch in pitches])
        max_pitch_len = torch.max(pitch_lens)
        pitches = torch.stack(
            [
                torch.nn.functional.pad(pitch, (0, max_pitch_len - pitch.shape[0]))
                for pitch in pitches
            ]
        )

        info["pitches"] = pitches
        info["pitch_lens"] = pitch_lens
        info["max_pitch_len"] = max_pitch_len

        return info
