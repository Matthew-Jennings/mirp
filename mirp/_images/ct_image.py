from typing import Any
import numpy as np
from mirp._images.generic_image import GenericImage


class CTImage(GenericImage):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def get_default_lowest_intensity():
        return -1000.0

    def update_image_data(self):
        if self.image_data is None:
            return

        # Ensure that CT values are Hounsfield units.
        self.image_data = np.round(self.image_data)

    def normalise_intensities(
            self,
            normalisation_method: None | str = "none",
            intensity_range: None | tuple[Any, Any] = None,
            saturation_range: None | tuple[Any, Any] = None,
            mask: None | np.ndarray = None
    ):
        """
        Normalise intensities. NOTE: this changes the class of the object from CTImage to GenericImage as
        normalisation breaks the one-to-one relationship between intensities and Hounsfield units.
        """
        image = super().normalise_intensities(
            normalisation_method=normalisation_method,
            intensity_range=intensity_range,
            saturation_range=saturation_range,
            mask=mask
        )

        if image.image_data is None:
            return self

        if normalisation_method is None or normalisation_method == "none":
            return self

        new_image = GenericImage(image_data=image.image_data)
        new_image.update_from_template(template=image)

        return new_image

    def scale_intensities(self, scale: float):

        image = super().scale_intensities(scale=scale)

        if image.image_data is None:
            return self

        if scale == 1.0:
            return self

        # Scaling intensities changes the object class from CTImage to GenericImage as this breaks the one-to-one
        # relationship between intensities and Hounsfield units.
        new_image = GenericImage(image_data=image.image_data)
        new_image.update_from_template(template=image)

        return new_image
