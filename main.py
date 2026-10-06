"""
Лабораторная работа №1. ООП в Python, исключения, XML и JSON.
Вариант 17: аудиоредактор.

Проекты (вместе с дорожками, клипами и эффектами) хранятся в JSON,
настройки экспорта - в XML.
"""

import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import TypeVar


# свои исключения
class AudioEditorError(Exception):
    """Общая ошибка программы."""


class EmptyNameError(AudioEditorError):
    """Пустое название."""


class InvalidTimeError(AudioEditorError):
    """Неправильное время."""


class InvalidVolumeError(AudioEditorError):
    """Неправильная громкость."""


class ItemNotFoundError(AudioEditorError):
    """Элемент не найден."""


class DataFormatError(AudioEditorError):
    """Ошибка при работе с файлом."""


# базовый класс
class AudioObject(ABC):
    """Базовый класс, у всех есть название."""

    def __init__(self, name: str) -> None:
        self.name = name  # идёт через setter

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value or not value.strip():
            raise EmptyNameError("Название не может быть пустым")
        self._name = value.strip()

    @abstractmethod
    def get_info(self) -> str:
        """Краткая информация."""

    def __str__(self) -> str:
        return self.get_info()


T = TypeVar("T", bound=AudioObject)


def find_by_name(items: list[T], name: str, kind: str) -> T:
    """Ищет объект по названию."""
    for item in items:
        if item.name == name.strip():
            return item
    raise ItemNotFoundError(f"Не найдено: {kind.lower()} «{name}»")


# эффекты
class Effect(AudioObject, ABC):
    """Эффект для клипа."""

    @abstractmethod
    def to_dict(self) -> dict:
        """Эффект в словарь (для JSON)."""

    @staticmethod
    def from_dict(data: dict) -> "Effect":
        """Эффект из словаря, тип смотрим по полю type."""
        try:
            kind = data["type"]
            if kind == "volume":
                return VolumeEffect(float(data["gain_db"]))
            if kind == "fade":
                return FadeEffect(data["fade_type"], float(data["seconds"]))
            if kind == "echo":
                return EchoEffect(int(data["delay_ms"]),
                                  float(data["decay"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise DataFormatError(f"Некорректные данные эффекта: {exc}") \
                from exc
        raise DataFormatError(f"Неизвестный тип эффекта: {kind!r}")


class VolumeEffect(Effect):
    """Громкость в дБ."""

    def __init__(self, gain_db: float) -> None:
        super().__init__("Громкость")
        if not -60 <= gain_db <= 24:
            raise InvalidVolumeError(
                f"Усиление {gain_db} дБ вне диапазона [-60, 24]")
        self.gain_db = gain_db

    def get_info(self) -> str:
        return f"Громкость {self.gain_db:+} дБ"

    def to_dict(self) -> dict:
        return {"type": "volume", "gain_db": self.gain_db}


class FadeEffect(Effect):
    """Плавное появление (in) или затухание (out)."""

    def __init__(self, fade_type: str, seconds: float) -> None:
        super().__init__("Затухание")
        if fade_type not in ("in", "out"):
            raise ValueError(f"Тип должен быть 'in' или 'out': {fade_type!r}")
        if seconds <= 0:
            raise InvalidTimeError("Длительность затухания должна быть > 0")
        self.fade_type = fade_type
        self.seconds = seconds

    def get_info(self) -> str:
        word = "появление" if self.fade_type == "in" else "затухание"
        return f"Плавное {word}, {self.seconds} с"

    def to_dict(self) -> dict:
        return {"type": "fade", "fade_type": self.fade_type,
                "seconds": self.seconds}


class EchoEffect(Effect):
    """Эхо."""

    def __init__(self, delay_ms: int, decay: float) -> None:
        super().__init__("Эхо")
        if delay_ms <= 0:
            raise ValueError(f"Задержка должна быть > 0, получено {delay_ms}")
        if not 0 < decay < 1:
            raise ValueError(f"Коэффициент должен быть в (0, 1): {decay}")
        self.delay_ms = delay_ms
        self.decay = decay

    def get_info(self) -> str:
        return f"Эхо: задержка {self.delay_ms} мс, затухание {self.decay}"

    def to_dict(self) -> dict:
        return {"type": "echo", "delay_ms": self.delay_ms,
                "decay": self.decay}


# клип
class AudioClip(AudioObject):
    """Кусок аудио на дорожке."""

    def __init__(self, name: str, file_path: str, start: float,
                 duration: float) -> None:
        super().__init__(name)
        self.file_path = file_path
        self.start = 0.0
        self.duration = 1.0
        self.move_to(start)           # проверка внутри
        self.set_duration(duration)   # проверка внутри
        self.effects: list[Effect] = []

    def move_to(self, start: float) -> None:
        """Двигает клип (секунды)."""
        if start < 0:
            raise InvalidTimeError(f"Начало клипа {start} с меньше нуля")
        self.start = start

    def set_duration(self, duration: float) -> None:
        """Меняет длительность."""
        if duration <= 0:
            raise InvalidTimeError(
                f"Длительность {duration} с должна быть > 0")
        self.duration = duration

    def get_end(self) -> float:
        """Когда клип заканчивается."""
        return self.start + self.duration

    # CRUD эффектов
    def add_effect(self, effect: Effect) -> None:
        self.effects.append(effect)

    def find_effect(self, name: str) -> Effect:
        return find_by_name(self.effects, name, "Эффект")

    def remove_effect(self, name: str) -> None:
        self.effects.remove(self.find_effect(name))

    def get_info(self) -> str:
        return (f"Клип «{self.name}» ({self.file_path}): "
                f"{self.start}–{self.get_end()} с, "
                f"эффектов: {len(self.effects)}")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "file_path": self.file_path,
            "start": self.start,
            "duration": self.duration,
            "effects": [effect.to_dict() for effect in self.effects],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AudioClip":
        try:
            clip = cls(data["name"], data["file_path"],
                       float(data["start"]), float(data["duration"]))
            for effect_data in data["effects"]:
                clip.add_effect(Effect.from_dict(effect_data))
            return clip
        except (KeyError, TypeError, ValueError) as exc:
            raise DataFormatError(f"Некорректные данные клипа: {exc}") from exc


# дорожка
class Track(AudioObject):
    """Дорожка с клипами."""

    def __init__(self, name: str, volume: int = 80,
                 muted: bool = False) -> None:
        super().__init__(name)
        self.volume = volume  # идёт через setter
        self.muted = muted
        self.clips: list[AudioClip] = []

    @property
    def volume(self) -> int:
        return self._volume

    @volume.setter
    def volume(self, value: int) -> None:
        if not 0 <= value <= 100:
            raise InvalidVolumeError(
                f"Громкость {value} вне диапазона [0, 100]")
        self._volume = value

    # CRUD клипов
    def add_clip(self, clip: AudioClip) -> None:
        self.clips.append(clip)

    def find_clip(self, name: str) -> AudioClip:
        return find_by_name(self.clips, name, "Клип")

    def remove_clip(self, name: str) -> None:
        self.clips.remove(self.find_clip(name))

    def get_duration(self) -> float:
        """Длина дорожки по последнему клипу."""
        return max((clip.get_end() for clip in self.clips), default=0.0)

    def get_info(self) -> str:
        state = "без звука" if self.muted else "звук включён"
        return (f"Дорожка «{self.name}»: громкость {self.volume}, {state}, "
                f"клипов: {len(self.clips)}")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "volume": self.volume,
            "muted": self.muted,
            "clips": [clip.to_dict() for clip in self.clips],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Track":
        try:
            track = cls(data["name"], int(data["volume"]),
                        bool(data["muted"]))
            for clip_data in data["clips"]:
                track.add_clip(AudioClip.from_dict(clip_data))
            return track
        except (KeyError, TypeError, ValueError) as exc:
            raise DataFormatError(
                f"Некорректные данные дорожки: {exc}") from exc


# метка
class Marker(AudioObject):
    """Метка на шкале времени."""

    def __init__(self, name: str, time: float) -> None:
        super().__init__(name)
        if time < 0:
            raise InvalidTimeError(f"Время метки {time} с меньше нуля")
        self.time = time

    def get_info(self) -> str:
        return f"Метка «{self.name}» на {self.time} с"

    def to_dict(self) -> dict:
        return {"name": self.name, "time": self.time}

    @classmethod
    def from_dict(cls, data: dict) -> "Marker":
        try:
            return cls(data["name"], float(data["time"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise DataFormatError(f"Некорректные данные метки: {exc}") from exc


# проект (хранится в JSON)
class Project(AudioObject):
    """Проект: дорожки и метки."""

    def __init__(self, name: str, sample_rate: int = 44100) -> None:
        super().__init__(name)
        if sample_rate <= 0:
            raise ValueError(
                f"Частота должна быть > 0, получено {sample_rate}")
        self.sample_rate = sample_rate
        self.tracks: list[Track] = []
        self.markers: list[Marker] = []

    # CRUD дорожек
    def add_track(self, track: Track) -> None:
        self.tracks.append(track)

    def find_track(self, name: str) -> Track:
        return find_by_name(self.tracks, name, "Дорожка")

    def remove_track(self, name: str) -> None:
        self.tracks.remove(self.find_track(name))

    # CRUD меток
    def add_marker(self, marker: Marker) -> None:
        self.markers.append(marker)

    def find_marker(self, name: str) -> Marker:
        return find_by_name(self.markers, name, "Метка")

    def remove_marker(self, name: str) -> None:
        self.markers.remove(self.find_marker(name))

    def get_duration(self) -> float:
        """Длина проекта по самой длинной дорожке."""
        return max((t.get_duration() for t in self.tracks), default=0.0)

    def average_track_volume(self) -> float:
        """Средняя громкость. Если дорожек нет, будет ZeroDivisionError."""
        return sum(t.volume for t in self.tracks) / len(self.tracks)

    def get_info(self) -> str:
        return (f"Проект «{self.name}» ({self.sample_rate} Гц): "
                f"дорожек {len(self.tracks)}, меток {len(self.markers)}, "
                f"длительность {self.get_duration()} с")

    # JSON
    def to_dict(self) -> dict:
        """Проект в словарь."""
        return {
            "name": self.name,
            "sample_rate": self.sample_rate,
            "markers": [marker.to_dict() for marker in self.markers],
            "tracks": [track.to_dict() for track in self.tracks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Проект из словаря."""
        try:
            project = cls(data["name"], int(data["sample_rate"]))
            for marker_data in data["markers"]:
                project.add_marker(Marker.from_dict(marker_data))
            for track_data in data["tracks"]:
                project.add_track(Track.from_dict(track_data))
            return project
        except (KeyError, TypeError, ValueError) as exc:
            raise DataFormatError(
                f"Некорректные данные проекта: {exc}") from exc


# настройки экспорта (хранятся в XML)
class ExportSettings(AudioObject):
    """Настройки экспорта."""

    FORMATS = ("wav", "mp3", "flac")

    def __init__(self, name: str, file_format: str, bitrate_kbps: int,
                 sample_rate: int) -> None:
        super().__init__(name)
        self.file_format = "wav"
        self.bitrate_kbps = 1
        self.update(file_format, bitrate_kbps)  # проверка внутри
        if sample_rate <= 0:
            raise ValueError(
                f"Частота должна быть > 0, получено {sample_rate}")
        self.sample_rate = sample_rate

    def update(self, file_format: str, bitrate_kbps: int) -> None:
        """Меняет формат и битрейт."""
        if file_format not in self.FORMATS:
            raise ValueError(f"Формат {file_format!r} не поддерживается")
        if bitrate_kbps <= 0:
            raise ValueError(f"Битрейт должен быть > 0: {bitrate_kbps}")
        self.file_format = file_format
        self.bitrate_kbps = bitrate_kbps

    def get_info(self) -> str:
        return (f"Экспорт «{self.name}»: {self.file_format}, "
                f"{self.bitrate_kbps} кбит/с, {self.sample_rate} Гц")

    # XML
    def to_xml(self) -> ET.Element:
        """Настройки в XML-элемент."""
        elem = ET.Element("export_settings")
        ET.SubElement(elem, "name").text = self.name
        ET.SubElement(elem, "file_format").text = self.file_format
        ET.SubElement(elem, "bitrate_kbps").text = str(self.bitrate_kbps)
        ET.SubElement(elem, "sample_rate").text = str(self.sample_rate)
        return elem

    @classmethod
    def from_xml(cls, element: ET.Element) -> "ExportSettings":
        """Настройки из XML-элемента."""
        try:
            return cls(
                name=element.findtext("name", ""),
                file_format=element.findtext("file_format", ""),
                bitrate_kbps=int(element.findtext("bitrate_kbps", "0")),
                sample_rate=int(element.findtext("sample_rate", "0")),
            )
        except (TypeError, ValueError) as exc:
            raise DataFormatError(
                f"Некорректные данные настроек экспорта: {exc}") from exc


# главный класс
class AudioEditor:
    """Аудиоредактор: хранит проекты и настройки, работает с файлами."""

    def __init__(self) -> None:
        self.projects: list[Project] = []
        self.presets: list[ExportSettings] = []

    # CRUD проектов
    def add_project(self, project: Project) -> None:
        self.projects.append(project)

    def find_project(self, name: str) -> Project:
        return find_by_name(self.projects, name, "Проект")

    def rename_project(self, old_name: str, new_name: str) -> None:
        self.find_project(old_name).name = new_name

    def remove_project(self, name: str) -> None:
        self.projects.remove(self.find_project(name))

    # CRUD настроек экспорта
    def add_preset(self, preset: ExportSettings) -> None:
        self.presets.append(preset)

    def find_preset(self, name: str) -> ExportSettings:
        return find_by_name(self.presets, name, "Настройки экспорта")

    def remove_preset(self, name: str) -> None:
        self.presets.remove(self.find_preset(name))

    # JSON: проекты
    def save_projects_json(self, path: str) -> None:
        """Сохраняет проекты в JSON."""
        data = [project.to_dict() for project in self.projects]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except OSError as exc:
            raise DataFormatError(
                f"Не удалось записать файл {path}: {exc}") from exc

    def load_projects_json(self, path: str) -> None:
        """Читает проекты из JSON."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise DataFormatError(
                f"Не удалось прочитать файл {path}: {exc}") from exc
        if not isinstance(data, list):
            raise DataFormatError(f"Ожидался список проектов в {path}")
        self.projects = [Project.from_dict(item) for item in data]

    # XML: настройки экспорта
    def save_presets_xml(self, path: str) -> None:
        """Сохраняет настройки в XML."""
        root = ET.Element("export_presets")
        for preset in self.presets:
            root.append(preset.to_xml())
        ET.indent(root)  # чтобы файл был читаемым
        try:
            ET.ElementTree(root).write(path, encoding="utf-8",
                                       xml_declaration=True)
        except OSError as exc:
            raise DataFormatError(
                f"Не удалось записать файл {path}: {exc}") from exc

    def load_presets_xml(self, path: str) -> None:
        """Читает настройки из XML."""
        try:
            tree = ET.parse(path)
        except (OSError, ET.ParseError) as exc:
            raise DataFormatError(
                f"Не удалось прочитать файл {path}: {exc}") from exc
        root = tree.getroot()
        if root.tag != "export_presets":
            raise DataFormatError(
                f"Корневой элемент должен быть <export_presets>, "
                f"найден <{root.tag}>")
        self.presets = [ExportSettings.from_xml(elem)
                        for elem in root.findall("export_settings")]

    def show_all(self) -> None:
        """Печатает всё на экран."""
        print("=" * 60)
        print("ПРОЕКТЫ (JSON):")
        for project in self.projects:
            print(" ", project)
            for marker in project.markers:
                print("     ", marker)
            for track in project.tracks:
                print("   -", track)
                for clip in track.clips:
                    print("       *", clip)
                    for effect in clip.effects:
                        print("           ~", effect)
        print("НАСТРОЙКИ ЭКСПОРТА (XML):")
        for preset in self.presets:
            print("  -", preset)
        print("=" * 60)


# проверка исключений
def demo_exceptions() -> None:
    """Показывает как ловятся ошибки."""
    print("\n--- Демонстрация обработки исключений ---")

    # пустое название
    try:
        Track("   ")
    except EmptyNameError as exc:
        print(f"[EmptyNameError] {exc}")

    # отрицательное время
    try:
        AudioClip("Вступление", "intro.wav", -5, 10)
    except InvalidTimeError as exc:
        print(f"[InvalidTimeError] {exc}")

    # громкость больше 100
    try:
        Track("Голос", volume=150)
    except InvalidVolumeError as exc:
        print(f"[InvalidVolumeError] {exc}")

    # такой дорожки нет
    try:
        Project("Тест").find_track("Нет такой дорожки")
    except ItemNotFoundError as exc:
        print(f"[ItemNotFoundError] {exc}")

    # ValueError: формат ogg не поддерживается
    try:
        ExportSettings("Тест", "ogg", 128, 44100)
    except ValueError as exc:
        print(f"[ValueError] {exc}")

    # ZeroDivisionError: в проекте нет дорожек
    try:
        Project("Пустой проект").average_track_volume()
    except ZeroDivisionError as exc:
        print(f"[ZeroDivisionError] {exc}")

    # в словаре нет нужного поля
    try:
        Effect.from_dict({"type": "volume"})
    except DataFormatError as exc:
        print(f"[DataFormatError] {exc}")

    # родительский класс ловит все свои ошибки
    try:
        AudioClip("Клип", "a.wav", 0, 0)
    except AudioEditorError as exc:
        print(f"[AudioEditorError] {type(exc).__name__}: {exc}")

    # две ошибки в одном except
    try:
        with open("no_such_file.json", "r", encoding="utf-8") as f:
            json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[FileNotFoundError/JSONDecodeError] {exc}")

    # else и finally
    try:
        value = float("2.5")
    except ValueError:
        print("Не число")
    else:
        print(f"[else] Преобразование успешно: {value}")
    finally:
        print("[finally] Блок finally выполняется всегда")


# создаём файлы с данными
def create_data_files() -> None:
    """Создаёт data_projects.json и data_export.xml."""
    editor = AudioEditor()

    # проект 1
    podcast = Project("Подкаст выпуск 1")
    voice = Track("Голос", 85)
    intro = AudioClip("Вступление", "voice_intro.wav", 0.0, 15.5)
    intro.add_effect(FadeEffect("in", 2.0))
    intro.add_effect(VolumeEffect(3.0))
    voice.add_clip(intro)
    voice.add_clip(AudioClip("Основная часть", "voice_main.wav", 15.5, 600.0))
    music = Track("Музыка", 40)
    background = AudioClip("Фоновая музыка", "music.mp3", 0.0, 615.5)
    background.add_effect(VolumeEffect(-12.0))
    background.add_effect(FadeEffect("out", 5.0))
    music.add_clip(background)
    podcast.add_track(voice)
    podcast.add_track(music)
    podcast.add_marker(Marker("Начало темы", 15.5))
    editor.add_project(podcast)

    # проект 2
    song = Project("Демо песни", 48000)
    vocal = Track("Вокал", 90)
    verse = AudioClip("Куплет 1", "vocal.wav", 4.0, 32.0)
    verse.add_effect(EchoEffect(300, 0.4))
    vocal.add_clip(verse)
    guitar = Track("Гитара", 70, muted=True)
    guitar.add_clip(AudioClip("Гитарный рифф", "guitar.wav", 0.0, 36.0))
    song.add_track(vocal)
    song.add_track(guitar)
    song.add_marker(Marker("Припев", 36.0))
    editor.add_project(song)

    # настройки экспорта
    editor.add_preset(ExportSettings("Для YouTube", "mp3", 192, 44100))
    editor.add_preset(ExportSettings("Для телефона", "mp3", 128, 44100))
    editor.add_preset(ExportSettings("Студийное качество", "wav", 1411,
                                     48000))

    editor.save_projects_json("data_projects.json")
    editor.save_presets_xml("data_export.xml")
    print("Созданы файлы: data_projects.json, data_export.xml")


# чтение из файлов
def read_data_files() -> AudioEditor:
    """Читает оба файла."""
    editor = AudioEditor()
    editor.load_projects_json("data_projects.json")
    editor.load_presets_xml("data_export.xml")
    return editor


# проверка CRUD
def demo_crud(editor: AudioEditor) -> None:
    """Показывает create, read, update, delete."""
    print("\n--- Демонстрация CRUD ---")

    # Read
    project = editor.find_project("Подкаст выпуск 1")
    print("[Read]", project.find_track("Голос"))

    # Create
    effects_track = Track("Звуковые эффекты", 60)
    effects_track.add_clip(AudioClip("Аплодисменты", "applause.wav",
                                     610.0, 5.0))
    project.add_track(effects_track)
    print("[Create]", effects_track)

    # Update
    project.find_track("Музыка").volume = 30
    effects_track.find_clip("Аплодисменты").move_to(615.0)
    editor.rename_project("Подкаст выпуск 1", "Подкаст. Выпуск 1")
    print("[Update]", project)

    # Delete
    project.remove_track("Звуковые эффекты")
    editor.remove_project("Демо песни")
    editor.remove_preset("Для телефона")
    print("[Delete] Остались:")
    editor.show_all()

    # удаляем то, чего нет
    try:
        editor.remove_project("Демо песни")
    except ItemNotFoundError as exc:
        print(f"[ItemNotFoundError] {exc}")


# запуск
def main() -> None:
    try:
        demo_exceptions()
        create_data_files()
        print("\n--- Чтение данных из файлов ---")
        editor = read_data_files()
        editor.show_all()
        demo_crud(editor)
    except AudioEditorError as exc:
        # программа не должна падать
        print(f"Ошибка в работе программы: {exc}")


if __name__ == "__main__":
    main()
