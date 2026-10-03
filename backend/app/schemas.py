from pydantic import BaseModel, Field, field_validator

class Credentials(BaseModel):
    username: str = Field(min_length=2, max_length=40, pattern=r'^[\w\-\u4e00-\u9fff]+$')
    password: str = Field(min_length=10, max_length=128)

    @field_validator('username')
    @classmethod
    def reserved_name(cls, value):
        if value.startswith('__'):
            raise ValueError('用户名不能以双下划线开头')
        return value

class SpaceInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    is_public: bool = False

    @field_validator('name', mode='before')
    @classmethod
    def normalize_name(cls, value):
        if isinstance(value, str):
            if '\x00' in value:
                raise ValueError('名称包含无效字符')
            return value.strip()
        return value

class PictureEdit(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=1000)
    tags: list[str] = Field(default_factory=list, max_length=8)

    @field_validator('title', mode='before')
    @classmethod
    def normalize_title(cls, value):
        if isinstance(value, str):
            if '\x00' in value:
                raise ValueError('名称包含无效字符')
            return value.strip()
        return value

    @field_validator('description')
    @classmethod
    def valid_description(cls, value):
        if '\x00' in value:
            raise ValueError('描述包含无效字符')
        return value

    @field_validator('tags')
    @classmethod
    def clean_tags(cls, tags):
        if any('\x00' in tag for tag in tags):
            raise ValueError('标签包含无效字符')
        result = list(dict.fromkeys(tag.strip().casefold() for tag in tags if tag.strip()))
        if any(len(tag) > 24 for tag in result):
            raise ValueError('标签不能超过 24 个字符')
        return result
