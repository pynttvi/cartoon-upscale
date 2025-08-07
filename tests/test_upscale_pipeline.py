import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json
import builtins

import upscale_pipeline


class TestUpscaleScript(unittest.TestCase):

    def print_run_commands(self, mock_run):
        print("\n🧪 run_command calls:")
        for i, call in enumerate(mock_run.call_args_list):
            cmd = call[0][0]
            if isinstance(cmd, list):
                cmd_str = " ".join(str(part) for part in cmd)
            else:
                cmd_str = str(cmd)
            print(f"  [{i}] {cmd_str}")

    @patch("upscale_pipeline.run_command")
    def test_extract_dvd(self, mock_run):
        upscale_pipeline.extract_dvd()
        mock_run.assert_called_once_with(
            [
                "bash",
                "0_extract_dvd_to_mp4.sh",
                upscale_pipeline.SETTINGS["input_path"],
            ]
        )
        self.print_run_commands(mock_run)

    @patch("upscale_pipeline.run_command")
    def test_preprocess_mp4(self, mock_run):
        upscale_pipeline.preprocess_mp4()
        mock_run.assert_called_once_with(
            [
                "bash",
                "1_preprocess_mp4.sh",
                upscale_pipeline.SETTINGS["input_path"],
            ]
        )
        self.print_run_commands(mock_run)

    @patch("upscale_pipeline.run_command")
    def test_extract_frames(self, mock_run):
        upscale_pipeline.extract_frames()
        mock_run.assert_called_once_with(
            [
                "bash",
                "2_extract_frames.sh",
                upscale_pipeline.SETTINGS["input_path"],
            ]
        )
        self.print_run_commands(mock_run)

    @patch("upscale_pipeline.run_command")
    def test_encode_video(self, mock_run):
        upscale_pipeline.encode_video()
        mock_run.assert_called_once_with(
            [
                "bash",
                "3_encode_final_mp4.sh",
                upscale_pipeline.SETTINGS["input_path"],
                upscale_pipeline.SETTINGS["final_encoder"],
            ]
        )
        self.print_run_commands(mock_run)

    @patch("upscale_pipeline.run_command")
    def test_concat_parts(self, mock_run):
        upscale_pipeline.SETTINGS["working_dir"] = "work_testvideo"
        upscale_pipeline.SETTINGS["file_name"] = "testvideo"

        upscale_pipeline.SETTINGS["final_output_folder"] = "finals"
        expected_cmd = [
            "bash",
            "4_concat_video_parts.sh",
            upscale_pipeline.SETTINGS["video_start_prepend"],
            (
                str(
                    Path(
                        "work_testvideo/",
                        "testvideo",
                    )
                )
            ),
            upscale_pipeline.SETTINGS["video_end_append"],
            Path("finals", "testvideo").stem + ".mp4",
        ]
        upscale_pipeline.concat_parts()
        mock_run.assert_called_once_with(expected_cmd)
        self.print_run_commands(mock_run)

    @patch("upscale_pipeline.run_command")
    @patch("upscale_pipeline.save_progress")
    @patch("upscale_pipeline.load_progress")
    @patch("upscale_pipeline.time.sleep", return_value=None)  # to avoid actual sleep
    def test_upscale_frames(
        self, mock_sleep, mock_load_progress, mock_save_progress, mock_run
    ):
        # Setup mock progress and mock frames
        mock_load_progress.return_value = {"processed": []}

        fake_input_dir = Path("work_test/frames")
        fake_output_dir = Path("work_test/output")

        # Patch Path.glob to simulate PNG frames
        mock_frames = [Path(f"frame_{i}.png") for i in range(5)]

        with patch("upscale_pipeline.Path.glob", return_value=mock_frames), patch(
            "upscale_pipeline.Path.mkdir", return_value=None
        ), patch("upscale_pipeline.Path.exists", return_value=False):

            upscale_pipeline.SETTINGS["working_dir"] = "work_test"
            upscale_pipeline.SETTINGS["batch_size"] = 2

            upscale_pipeline.upscale_frames()

            # Ensure run_command is called once per frame
            self.assertEqual(mock_run.call_count, len(mock_frames))
            self.assertEqual(mock_save_progress.call_count, 3)  # After each batch

            # Check if frame names are passed correctly to run_command
            for i, frame in enumerate(mock_frames):
                called_args = mock_run.call_args_list[i][0][0]
                self.assertIn(str(frame), called_args)
        self.print_run_commands(mock_run)


if __name__ == "__main__":
    unittest.main()
