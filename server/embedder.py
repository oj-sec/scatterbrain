"""
Module to generate text embeddings using a SetenceTransformer model.
"""

import logging

import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from pacmap import PaCMAP
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim


class Embedder:
    """
    Class to generate text embeddings using a SentenceTransformer model.
    """

    def __init__(self, model, dimensions):
        logging.info(
            "Embedder initialising with parameters:\n\t-model name: %s\n\t-dimensions: %d",
            model,
            dimensions,
        )
        self.model = model
        self.dimensions = dimensions
        self.data = []
        self.comparison_data = []
        self.embeddings = []
        self.comparison_embeddings = []
        self.map_embeddings = []
        logging.info("Embedder initialised")

    def reset_states(self):
        """
        Method to reset the state of the embedder.
        """
        logging.info("Embedder resetting states.")
        self.data = []
        self.comparison_data = []
        self.embeddings = []
        self.comparison_embeddings = []
        self.map_embeddings = []
        logging.info("Embedder states reset.")

    def check_model(self):
        """
        Method to check if the model has been downloaded
        and load it if available. Can be optionally called
        before download_model() to indicate to a client
        that a download is required.

        Returns:
            bool: True if the model is loaded, False otherwise.
        """
        logging.info("Embedder checking for model file.")
        if self.model is None:
            logging.info("Embedder model not specified.")
            return False
        try:
            self.model = SentenceTransformer(
                self.model, truncate_dim=self.dimensions, local_files_only=True
            )
        except Exception as e:
            if "couldn't find it in the cached files" in str(e):
                logging.info("Embedder model not found.")
                return False
            else:
                logging.error("Embedder failed to check model. %s", e)
                raise e
        logging.info("Embedder model found.")
        return True

    def download_model(self):
        """
        Method to download and load a model.

        Raises:
            Exception: If the model fails to download.
        """
        logging.info("Embedder downloading model.")
        try:
            self.model = SentenceTransformer(self.model, truncate_dim=self.dimensions)
        except Exception as e:
            logging.error("Embedder failed to download model. %s", e)
            raise e
        logging.info("Embedder model loaded.")
        return

    def embed_text(self, row, field, overflow="truncate"):
        """
        Method to generate embeddings for a given text.

        Args:
            row (dict): A dictionary containing the data row.
            field (str): The field in the dictionary containing the text.
            overflow (str): The method to handle text overflow.

        Returns:
            list[float]: The embeddings of the text.
        """
        logging.info("Embedder embedding text.")
        if overflow == "average":
            texts = self.__chunk_text(row[field])
        else:
            texts = [row[field]]
        with open("data.txt", "a") as f:
            f.write(str(texts) + "\n")
        embedding_list = []
        for text in texts:
            try:
                embedding_list.append(self.model.encode(text))
            except Exception as e:
                logging.error("Embedder failed to embed text. %s", e)
                raise e
        if len(embedding_list) > 1:
            embeddings = np.mean(embedding_list, axis=0)
        else:
            embeddings = embedding_list[0]
        self.embeddings.append(embeddings)
        self.data.append(row)
        logging.info("Embedder text embedded.")
        return embeddings

    def __chunk_text(self, text, token_length=512, overlap_tokens=20):
        """
        Private method to split a text into chunks of a given token length.

        Args:
            text (str): The text to split.
            token_length (int): The maximum token length for each chunk.
            overlap_tokens (int): The number of overlapping tokens between chunks.

        Returns:
            list[str]: The split text chunks.
        """
        logging.info("Embedder splitting text.")
        tokens = self.model.tokenizer(
            text, return_tensors="pt", truncation=False, padding=False
        )
        if len(tokens["input_ids"][0]) <= token_length:
            return [text]
        input_ids = tokens["input_ids"][0]
        chunks = []
        for i in range(0, len(input_ids), token_length - overlap_tokens):
            chunk_ids = input_ids[i : i + token_length]
            chunk_text = self.model.tokenizer.decode(
                chunk_ids, skip_special_tokens=True
            )
            chunks.append(chunk_text)
        logging.info("Embedder text split into %d chunks.", len(chunks))
        for chunk in chunks:
            logging.info("Chunk: %s", chunk)
        return chunks

    def embed_comparison_text(self, text):
        """
        Method to generate embeddings for a comparison text.
        """
        logging.info("Embedder embedding comparison text.")
        try:
            embeddings = self.model.encode(text)
        except Exception as e:
            logging.error("Embedder failed to embed comparison text. %s", e)
            raise e
        self.comparison_embeddings.append(embeddings)
        self.comparison_data.append(text)
        logging.info("Embedder comparison text embedded.")
        return embeddings

    def compare_embeddings(self, text):
        """
        Method to get the closest comparison text to a given text.
        """
        logging.info("Embedder looking up comparison text.")
        if len(self.comparison_embeddings) == 0:
            logging.error(
                "Embedder failed to look up comparison text. No comparison text available."
            )
            raise ValueError("No comparison text available.")
        try:
            text_embedding = self.model.encode([text])
            similarities = cos_sim(text_embedding, self.comparison_embeddings)
            closest_index = similarities.argmax()
            closest_text = self.comparison_data[closest_index]
        except Exception as e:
            logging.error("Embedder failed to look up comparison text. %s", e)
            raise e
        logging.info("Embedder comparison text looked up.")
        return closest_text

    def reduce_dimensions(self, plot_dimensions=2):
        """
        Method to project the embeddings into a lower-dimensional space.
        """
        logging.info("Embedder reducing dimensions.")
        if isinstance(plot_dimensions, str):
            plot_dimensions = int(plot_dimensions)
        config = dict(
            n_neighbors=None,
            apply_pca=False,
            save_tree=True,
            verbose=True,
        )
        projection_model = PaCMAP(
            n_components=plot_dimensions,
            **config,
        )
        map_vectors = projection_model.fit_transform(self.embeddings).tolist()
        self.map_embeddings = map_vectors
        logging.info("Embedder dimensions reduced.")
        return True

    def generate_scatter(self, target_field, cmap="mako", category=None):
        """
        Method to generate a scatter plot of the embeddings.
        """
        logging.info("Embedder generating scatter plot.")
        plot_dimensions = len(self.map_embeddings[0])
        if plot_dimensions == 2:
            fig = self.__generate_2d_scatter(target_field, cmap, category)
        elif plot_dimensions == 3:
            fig = self.__generate_3d_scatter(target_field, cmap, category)
        else:
            logging.error(
                "Embedder failed to generate scatter plot. Invalid plot dimensions."
            )
            raise ValueError("Invalid plot dimensions.")

        dark_color = self.__get_hex_colour(sns.color_palette(cmap, as_cmap=True)(0.1))
        fig.update_layout(
            paper_bgcolor="rgba(0, 0, 0, 0)",
            font=dict(family="Courier New, monospace", size=18, color=dark_color),
            hoverlabel=dict(
                bgcolor=dark_color,
                font_family="Courier New, monospace",
                font_color="white",
            ),
        )
        plotHTML = fig.to_html(full_html=True, include_plotlyjs=True)
        logging.info("Embedder scatter plot generated.")
        return plotHTML

    def __generate_2d_scatter(self, target_field, cmap, category):
        """
        Method to generate a 2D scatter plot of the embeddings.
        """
        logging.info("Embedder generating 2D scatter plot.")
        df = pd.DataFrame(self.map_embeddings, columns=["x", "y"])
        df["text"] = [row[target_field] for row in self.data]
        df["text"] = df["text"].apply(lambda x: self.__split_text(x))
        fig = go.Figure()
        if category == "" or category is None:
            fig.add_trace(
                go.Scatter(
                    x=df["x"],
                    y=df["y"],
                    mode="markers",
                    marker=dict(
                        color=self.__get_hex_colour(
                            sns.color_palette(cmap, as_cmap=True)(0.1)
                        )
                    ),
                    text=df["text"],
                    hoverinfo="text",
                )
            )
        else:
            df[category] = [row[category] for row in self.data]
            categories = df[category].unique()
            colours = {
                category: self.__get_hex_colour(
                    sns.color_palette(cmap, as_cmap=True)(i / len(categories))
                )
                for i, category in enumerate(categories)
            }
            for i, icategory in enumerate(categories):
                category_df = df[df[category] == icategory]
                fig.add_trace(
                    go.Scatter(
                        x=category_df["x"],
                        y=category_df["y"],
                        mode="markers",
                        marker=dict(color=colours[icategory], size=10),
                        text=category_df["text"],
                        name=icategory,
                        hoverinfo="text",
                        hovertemplate="<b>%{text}</b><extra></extra>",
                    )
                )
        return fig

    def __generate_3d_scatter(self, target_field, cmap, category):
        """
        Method to generate a 3D scatter plot of the embeddings.
        """
        logging.info("Embedder generating 3D scatter plot.")
        df = pd.DataFrame(self.map_embeddings, columns=["x", "y", "z"])
        df["text"] = [row[target_field] for row in self.data]
        df["text"] = df["text"].apply(lambda x: self.__split_text(x))
        fig = go.Figure()
        if category == "" or category is None:
            fig.add_trace(
                go.Scatter3d(
                    x=df["x"],
                    y=df["y"],
                    z=df["z"],
                    mode="markers",
                    marker=dict(
                        color=self.__get_hex_colour(
                            sns.color_palette(cmap, as_cmap=True)(0.1)
                        )
                    ),
                    text=df["text"],
                    hoverinfo="text",
                )
            )
        else:
            df[category] = [row[category] for row in self.data]
            categories = df[category].unique()
            colours = {
                category: self.__get_hex_colour(
                    sns.color_palette(cmap, as_cmap=True)(i / len(categories))
                )
                for i, category in enumerate(categories)
            }
            for i, icategory in enumerate(categories):
                category_df = df[df[category] == icategory]
                fig.add_trace(
                    go.Scatter3d(
                        x=category_df["x"],
                        y=category_df["y"],
                        z=category_df["z"],
                        mode="markers",
                        marker=dict(color=colours[icategory], size=10),
                        text=category_df["text"],
                        name=icategory,
                        hoverinfo="text",
                        hovertemplate="<b>%{text}</b><extra></extra>",
                    )
                )
        return fig

    def __split_text(self, text, max_length=100):
        """
        Method to split a text into chunks of a given maximum length.
        """
        words = text.split()
        split_words = []
        for word in words:
            if len(word) > max_length:
                divisor = len(word) // max_length
                for i in range(divisor + 1):
                    split_words.append(word[i * max_length : (i + 1) * max_length])
            else:
                split_words.append(word)
        lines = []
        buffer = ""
        for word in split_words:
            if len(buffer) + len(word) > max_length:
                lines.append(buffer)
                buffer = word
            else:
                buffer += " " + word
        lines.append(buffer)
        lines = [line.strip() for line in lines]
        return "<br>".join(lines)

    def __get_hex_colour(self, seaborn_colour):
        """
        Method to convert a seaborn colour to a matplotlib colour.
        """
        matplotlib_colour = mcolors.to_hex(seaborn_colour)
        return matplotlib_colour
