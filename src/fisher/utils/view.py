from datetime import datetime

from discord import Colour, Embed, Interaction, ui


class PaginationEmbed(ui.View):
    def __init__(
        self,
        timeout: int = 60,
        *,
        color: Colour | int = None,
        title: str = None,
        type: str = "rich",
        url: str = None,
        description: str = None,
        timestamp: datetime = None,
    ):
        super().__init__(timeout=timeout)
        self.color = color
        self.title = title
        self.type = type
        self.url = url
        self.description = description
        self.timestamp = timestamp

        self.embed = Embed(
            color=self.color,
            title=self.title,
            type=self.type,
            url=self.url,
            description=self.description,
            timestamp=self.timestamp,
        )
        self.pages: list[list[int]] = []
        self.fields: list[tuple[str, str, bool]] = []
        self.previous_page.disabled = True
        self.current_page = 1

    @property
    def initial_embed(self):
        embed = self.embed.copy()
        if max(1, len(self.pages)) == 1:
            self.next_page.disabled = True
        if not self.fields:
            return embed
        for field_index in self.pages[0]:
            embed.add_field(
                name=self.fields[field_index][0],
                value=self.fields[field_index][1],
                inline=self.fields[field_index][2],
            )
        return embed

    def embed_update_callback(self):
        self.pages.clear()
        cur_page_length = len(self.embed)
        cur_page_field_num = 0
        for i, field in enumerate(self.fields):
            if (
                cur_page_length + len(field[0]) + len(field[1]) > 6000
                or cur_page_field_num + 1 > 25
            ):
                self.pages.append([i])
                cur_page_length = len(self.embed) + len(field[0]) + len(field[1])
                cur_page_field_num = 1
            else:
                cur_page_length += len(field[0]) + len(field[1])
                cur_page_field_num += 1
                self.pages[-1].append(i)
        self.page_number.label = f"{self.current_page}/{len(self.pages)}"

    def set_author(self, *, name, url: str = None, icon_url: str = None):
        self.embed.set_author(name=name, url=url, icon_url=icon_url)
        self.embed_update_callback()

    def remove_author(self):
        self.embed.remove_author()
        self.embed_update_callback()

    def set_footer(self, *, text: str = None, icon_url: str = None):
        self.embed.set_footer(text=text, icon_url=icon_url)
        self.embed_update_callback()

    def remove_footer(self):
        self.embed.remove_footer()
        self.embed_update_callback()

    def set_image(self, *, url: str = None):
        self.embed.set_image(url=url)

    def set_thumbnail(self, *, url: str = None):
        self.embed.set_thumbnail(url=url)

    def add_field(self, name, value, inline=False):
        self.fields.append((name, value, inline))
        if not self.pages:
            self.pages.append([0])
            return
        last_page_field_num = len(self.pages[-1])
        if last_page_field_num + 1 > 25:
            self.pages.append([len(self.fields) - 1])
            self.page_number.label = f"{self.current_page}/{len(self.pages)}"
            return
        last_page_length = len(self.embed)
        for field_index in self.pages[-1]:
            last_page_length += len(self.fields[field_index][0]) + len(
                self.fields[field_index][1]
            )
        if last_page_length + len(name) + len(value) > 6000:
            self.pages.append([len(self.fields) - 1])
        else:
            self.pages[-1].append(len(self.fields) - 1)
        self.page_number.label = f"{self.current_page}/{len(self.pages)}"

    def clear_fields(self):
        self.fields.clear()
        self.pages.clear()
        self.page_number.label = f"{self.current_page}/{min(1, len(self.pages))}"

    async def update_button(self):
        if self.current_page == 1:
            self.previous_page.disabled = True
        else:
            self.previous_page.disabled = False

        if self.current_page == len(self.pages):
            self.next_page.disabled = True
        else:
            self.next_page.disabled = False

        self.page_number.label = f"{self.current_page}/{len(self.pages)}"

    @ui.button(emoji="⬅️")
    async def previous_page(self, interaction: Interaction, button: ui.Button):
        embed = self.embed.copy()
        self.current_page -= 1
        for field_index in self.pages[self.current_page - 1]:
            embed.add_field(
                name=self.fields[field_index][0],
                value=self.fields[field_index][1],
                inline=self.fields[field_index][2],
            )
        await self.update_button()
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(label="1/1", disabled=True)
    async def page_number(self, interaction: Interaction, button: ui.Button):
        pass

    @ui.button(emoji="➡️")
    async def next_page(self, interaction: Interaction, button: ui.Button):
        embed = self.embed.copy()
        self.current_page += 1
        for field_index in self.pages[self.current_page - 1]:
            embed.add_field(
                name=self.fields[field_index][0],
                value=self.fields[field_index][1],
                inline=self.fields[field_index][2],
            )
        await self.update_button()
        await interaction.response.edit_message(embed=embed, view=self)
