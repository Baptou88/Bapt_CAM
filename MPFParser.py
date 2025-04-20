

class abstractParser:

    def __init__(self, content):
        self.content = content
        self.cursor = 0
        self.char = ''
        self.operations = []
        pass

    def next(self):
        if not self.hasNext():
            return False
        self.cursor += 1
        self.char = self.content[self.cursor]
        return self.char

    def hasNext(self):
        return self.cursor < len(self.content) -1

    def get(self):
        return self.content[self.cursor]

    def exceptFloat(self):
        if not (self.char.isdigit() or self.char in ['+','-','.',',']):
            raise Exception(f"Invalid number, Number Excepted got {self.char}")
        start = self.cursor
        while self.hasNext() and (self.char.isdigit() or self.char in ['+','-','.',',']):
            self.cursor += 1
            self.char = self.content[self.cursor]
        end = self.cursor
        return float(self.content[start:end])
    
    def exceptInt(self):
        char = self.get()
        if not (char.isdigit() or char in ['+','-']):
            raise Exception(f"Invalid number, Number Excepted got {char}")
        start = self.cursor
        while self.hasNext() and char.isdigit():
            char = self.next()
        end = self.cursor
        return int(self.content[start:end])

    def getLineFromCursor(self):
        lignes = self.content.split('\n')
        debut = 0
        for i in range(len(lignes)):
            l = len(lignes[i])
            fin = debut + l
            if self.cursor >= debut and self.cursor <= fin :
                return {"Line":lignes[i], "Number":i+1, 'start':debut, 'end':fin}
            debut += len(lignes[i]) + 1
        return None
class MPFParser(abstractParser):
    def __init__(self, content):
        super().__init__(content)
        pass

    def commentaire(self):
        self.char = self.content[self.cursor]
        while self.cursor < len(self.content) and self.char != '\n':
            self.cursor += 1
            self.char = self.content[self.cursor]

    def numLine(self):
        self.char = self.content[self.cursor]
        while self.cursor < len(self.content) and self.char.isdigit():
            self.cursor += 1
            self.char = self.content[self.cursor]

    def toolSpindle(self):
        self.cursor += 1
        if not self.content[self.cursor].isdigit():
            raise Exception(f"Invalid spindle, Number Excepted got {self.content[self.cursor]}")
        start = self.cursor
        self.char = self.content[self.cursor]
        while self.cursor < len(self.content) and self.char.isdigit():
            self.cursor += 1
            self.char = self.content[self.cursor]
        end = self.cursor
        spindle = int(self.content[start:end])
        #self.cursor += 1
        a= self.content[self.cursor]
        a=0
        return spindle

    def tool(self):
        self.char = self.content[self.cursor]
        spindle = -1
        while self.cursor < len(self.content) and not self.char.isdigit():
            self.cursor += 1
            self.char = self.content[self.cursor]
        start = self.cursor
        while self.cursor < len(self.content) and self.char.isdigit():
            self.cursor += 1
            self.char = self.content[self.cursor]
        end = self.cursor
        toolNumber = int(self.content[start:end])
        
        while self.cursor < len(self.content) and self.content[self.cursor] != '\n':
            self.cursor += 1
            char = self.content[self.cursor]
            
            if char == 'S':
                spindle = self.toolSpindle()
                a= self.content[self.cursor]
                a=0
        self.cursor += 1
        a= self.content[self.cursor]
        a=0
        return {"Type":"toolCall","T":toolNumber, "S":spindle}
        
    def gcode(self):
        """Parse a G-code command, return a dictionary with command number and coordinates (X, Y, Z)"""
        char = self.get()
        command = self.exceptInt()
        gCommand = ["G" + str(command)]
        
        while self.hasNext() and self.get() != '\n':
            char = self.next()
            if char == ' ':
                pass
            elif char == ';':
                raise Exception("Unimplemented commentaire in line")
            elif char in ['X','Y','Z']:

                c = self.coordinate()
                gCommand.append(c)
            else:
                raise Exception(f"Invalid G-code, Invalid key {char} at pos {self.cursor} at line {self.getLineFromCursor()}")
        self.next()
        return {"Type":"gcode","G":gCommand}

    def coordinate(self):
        """
        Parse coordinate values from the content string at the current cursor 
        position. This function updates cursor position and collects coordinate 
        values (X, Y, Z) or M-code commands, while checking for duplicates and 
        invalid keys. Returns a dictionary of parsed coordinates.
        """
        key = self.get()
        char = self.next()

        numb = self.exceptFloat()
        
        coordinate = {key: numb}
        while self.hasNext() and self.char != '\n':
            char = self.next()
            if char == ' ':
                pass
            elif char == ';':
                pass
            elif char in ['X', 'Y', 'Z', 'I', 'J', 'K']:
                c = self.coordinate()
                
                if any(k == c for k in coordinate):
                    raise Exception(f"Invalid coordinate, Duplicate key {char}")
                coordinate.update(c)
            elif char in ['M']:
                self.next()
                m = self.mcode()
                
                coordinate.update(m)
            else:
                raise Exception(f"Invalid coordinate, Invalid key {char}")
        return coordinate

    def mcode(self):
        char = self.get()
        code = self.exceptInt()
        mCommand = ["M" + str(code)]
        #self.cursor += 1
        char = self.get()
        while self.hasNext() and char != '\n':
            char = self.next()
            if char == 'M':
                m = self.mcode()
                if m in mCommand:
                    raise Exception(f"Invalid M-code, Duplicate key {m}")
                mCommand.append(m)
            elif char == ';':
                pass
            else:
                raise Exception(f"Invalid M-code, Invalid key {char}")
        #self.next()
        return {"Type":"mcode","M":mCommand}

    def parse(self):
        while self.hasNext():
            char = self.get()
            self.cursor += 1

            if char == ' ':
                pass
            if char == "\n":
                pass
            elif char == ';':
                self.commentaire()
            elif char == 'N':
                self.numLine()
            elif char == 'T':
                self.operations.append(self.tool())
                print(f'cursor: {self.cursor}')
                a=0
            elif char == 'G':
                self.operations.append(self.gcode())
                a = self.cursor
                b= self.get()
            elif char in ['X','Y','Z']:
                self.cursor -= 1
                self.operations.append(self.coordinate())
            elif char == 'M':
                self.operations.append(self.mcode())
                self.next()
            else:
                raise Exception(f"Invalid character '{char}' at position {self.cursor}\n line: {self.getLineFromCursor()}")
                
            

        return self.operations

if __name__ == "__main__":
    with open("FAO/test.MPF", "r") as file:
        content = file.read()
        parser = MPFParser(content)
        operations = parser.parse()
        print(operations)
