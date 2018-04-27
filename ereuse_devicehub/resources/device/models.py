from contextlib import suppress
from typing import Dict, Set

from ereuse_utils.naming import Naming
from sqlalchemy import BigInteger, Column, Float, ForeignKey, Integer, Sequence, SmallInteger, \
    Unicode, inspect
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import backref, relationship

from ereuse_devicehub.resources.models import STR_BIG_SIZE, STR_SIZE, STR_SM_SIZE, Thing, \
    check_range
from teal.db import CASCADE, POLYMORPHIC_ID, POLYMORPHIC_ON, ResourceNotFound


class Device(Thing):
    id = Column(BigInteger, Sequence('device_seq'), primary_key=True)  # type: int
    type = Column(Unicode(STR_SM_SIZE), nullable=False)
    hid = Column(Unicode(STR_BIG_SIZE), unique=True)  # type: str
    pid = Column(Unicode(STR_SIZE))  # type: str
    gid = Column(Unicode(STR_SIZE))  # type: str
    model = Column(Unicode(STR_BIG_SIZE))  # type: str
    manufacturer = Column(Unicode(STR_SIZE))  # type: str
    serial_number = Column(Unicode(STR_SIZE))  # type: str
    weight = Column(Float(precision=3, decimal_return_scale=3),
                    check_range('weight', 0.1, 3))  # type: float
    width = Column(Float(precision=3, decimal_return_scale=3),
                   check_range('width', 0.1, 3))  # type: float
    height = Column(Float(precision=3, decimal_return_scale=3),
                    check_range('height', 0.1, 3))  # type: float

    @property
    def physical_properties(self) -> Dict[Column, object or None]:
        """
        Fields that describe the physical properties of a device.

        :return A generator where each value is a tuple with tho fields:
                - Column.
                - Actual value of the column or None.
        """
        # todo ensure to remove materialized values when start using them
        # todo or self.__table__.columns if inspect fails
        return {c: getattr(self, c.name, None)
                for c in inspect(self.__class__).attrs
                if not c.foreign_keys and c not in {self.id, self.type}}

    @declared_attr
    def __mapper_args__(cls):
        """
        Defines inheritance.

        From `the guide <http://docs.sqlalchemy.org/en/latest/orm/
        extensions/declarative/api.html
        #sqlalchemy.ext.declarative.declared_attr>`_
        """
        args = {POLYMORPHIC_ID: cls.__name__}
        if cls.__name__ == 'Device':
            args[POLYMORPHIC_ON] = cls.type
        return args

    def __init__(self, *args, **kw) -> None:
        super().__init__(*args, **kw)
        with suppress(TypeError):
            self.hid = Naming.hid(self.manufacturer, self.serial_number, self.model)


class Computer(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)  # type: int


class Desktop(Computer):
    pass


class Laptop(Computer):
    pass


class Netbook(Computer):
    pass


class Server(Computer):
    pass


class Microtower(Computer):
    pass


class Component(Device):
    id = Column(BigInteger, ForeignKey(Device.id), primary_key=True)  # type: int

    parent_id = Column(BigInteger, ForeignKey('computer.id'))
    parent = relationship(Computer,
                          backref=backref('components', lazy=True, cascade=CASCADE),
                          primaryjoin='Component.parent_id == Computer.id')  # type: Device

    def similar_one(self, parent: Computer, blacklist: Set[int]) -> 'Component':
        """
        Gets a component that:
        - has the same parent.
        - Doesn't generate HID.
        - Has same physical properties.
        :param parent:
        :param blacklist: A set of components to not to consider
                          when looking for similar ones.
        """
        assert self.hid is None, 'Don\'t use this method with a component that has HID'
        component = self.__class__.query \
            .filter_by(parent=parent, hid=None, **self.physical_properties) \
            .filter(~Component.id.in_(blacklist)) \
            .first()
        if not component:
            raise ResourceNotFound(self.type)
        return component


class GraphicCard(Component):
    id = Column(BigInteger, ForeignKey(Component.id), primary_key=True)  # type: int
    memory = Column(SmallInteger, check_range('memory', min=1, max=10000))  # type: int


class HardDrive(Component):
    id = Column(BigInteger, ForeignKey(Component.id), primary_key=True)  # type: int
    size = Column(Integer, check_range('size', min=1, max=10 ** 8))  # type: int


class Motherboard(Component):
    id = Column(BigInteger, ForeignKey(Component.id), primary_key=True)  # type: int
    slots = Column(SmallInteger, check_range('slots'))  # type: int
    usb = Column(SmallInteger, check_range('usb'))  # type: int
    firewire = Column(SmallInteger, check_range('firewire'))  # type: int
    serial = Column(SmallInteger, check_range('serial'))  # type: int
    pcmcia = Column(SmallInteger, check_range('pcmcia'))  # type: int


class NetworkAdapter(Component):
    id = Column(BigInteger, ForeignKey(Component.id), primary_key=True)  # type: int
    speed = Column(SmallInteger, check_range('speed', min=10, max=10000))  # type: int


class RamModule(Component):
    id = Column(BigInteger, ForeignKey(Component.id), primary_key=True)  # type: int
    size = Column(SmallInteger, check_range('size', min=128, max=17000))
    speed = Column(Float, check_range('speed', min=100, max=10000))