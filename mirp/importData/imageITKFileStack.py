import warnings
import itk
import numpy as np
import pandas as pd
from typing import List

from mirp.importData.imageITKFile import ImageITKFile
from mirp.importData.imageGenericFileStack import ImageFileStack


class ImageITKFileStack(ImageFileStack):

    def __init__(
            self,
            image_file_objects: List[ImageITKFile],
            **kwargs
    ):
        super().__init__(image_file_objects, **kwargs)

    def complete(self, remove_metadata=True, force=False):
        # Load metadata of every slice.
        self.load_metadata()

        self._complete_modality()
        self._complete_sample_name()

        # Placeholders for slice positions.
        image_position_z = [0.0] * len(self.image_file_objects)
        image_position_y = [0.0] * len(self.image_file_objects)
        image_position_x = [0.0] * len(self.image_file_objects)

        for ii, image_object in enumerate(self.image_file_objects):
            slice_origin = np.array(image_object.image_metadata.GetOrigin())[::-1]

            image_position_z[ii] = slice_origin[0]
            image_position_y[ii] = slice_origin[1]
            image_position_x[ii] = slice_origin[2]

        # Order ascending position (DICOM: z increases from feet to head)
        position_table = pd.DataFrame({
            "original_object_order": list(range(len(self.image_file_objects))),
            "position_z": image_position_z,
            "position_y": image_position_y,
            "position_x": image_position_x
        }).sort_values(by=["position_z", "position_y", "position_x"])

        # Sort image file objects.
        self.image_file_objects = [
            self.image_file_objects[position_table.original_object_order[ii]]
            for ii in range(len(position_table))
        ]

        # Set image origin.
        self.image_origin = tuple(np.array(self.image_file_objects[0].image_metadata.GetOrigin())[::-1])

        # Set image spacing. Compute the distance between the origins of the slices. This is the slice spacing.
        image_slice_spacing = np.sqrt(
            np.power(np.diff(position_table.position_x.values), 2.0) +
            np.power(np.diff(position_table.position_y.values), 2.0) +
            np.power(np.diff(position_table.position_z.values), 2.0))

        # Find the smallest slice spacing.
        min_slice_spacing = np.min(image_slice_spacing)

        # Find how much other slices differ.
        image_slice_spacing_multiplier = image_slice_spacing / min_slice_spacing

        if np.any(image_slice_spacing_multiplier > 1.2):
            warnings.warn(
                f"Inconsistent distance between slice origins of subsequent slices: {np.unique(image_slice_spacing)}. "
                "Slices cannot be aligned correctly. This is likely due to missing slices. "
                "MIRP will attempt to interpolate the missing slices and their ROI masks for volumetric analysis.",
                UserWarning)

            # Update slice positions.
            self.slice_positions = list(np.cumsum(np.insert(np.around(image_slice_spacing, 5), 0, 0.0)))

        # Determine image slice spacing.
        image_slice_spacing = np.around(np.mean(image_slice_spacing[image_slice_spacing_multiplier <= 1.2]), 5)

        # Set image spacing.
        image_spacing = np.array(self.image_file_objects[0].image_metadata.GetSpacing())[::-1]
        if image_spacing[0] == image_slice_spacing:
            self.image_spacing = tuple(image_spacing)
        else:
            self.image_spacing = tuple([image_slice_spacing, image_spacing[1], image_spacing[2]])

        # Read orientation metadata.
        image_orientation = np.reshape(np.ravel(itk.array_from_matrix(
            self.image_file_objects[0].image_metadata.GetDirection()))[::-1], [3, 3])

        # Add (Zx, Zy, Zz)
        z_orientation = np.array([
            np.around(np.min(np.diff(position_table.position_z.values)), 5),
            np.around(np.min(np.diff(position_table.position_y.values)), 5),
            np.around(np.min(np.diff(position_table.position_x.values)), 5)
        ]) / image_slice_spacing

        # Replace z-orientation and set image_orientation.
        image_orientation[0, :] = z_orientation
        self.image_orientation = image_orientation

        # Set dimension
        image_dimension = np.array(self.image_metadata.GetSize())[::-1]

        self.image_dimension = tuple([len(position_table), image_dimension[1], image_dimension[2]])

        # Check if the complete data passes verification.
        self.check(raise_error=True, remove_metadata=False)
